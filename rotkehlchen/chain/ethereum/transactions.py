import logging
from collections import defaultdict
from typing import Dict, List, Optional, Set

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.errors import RemoteError
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import ChecksumEthAddress, EthereumTransaction, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import LockableQueryObject, protect_with_lock

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

FREE_ETH_TX_LIMIT = 250


class EthTransactions(LockableQueryObject):

    def __init__(
            self,
            database: DBHandler,
            etherscan: Etherscan,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__()
        self.database = database
        self.etherscan = etherscan
        self.msg_aggregator = msg_aggregator
        self.tx_per_address: Dict[ChecksumEthAddress, int] = defaultdict(int)

    def _return_transactions_maybe_limit(
            self,
            address: ChecksumEthAddress,
            transactions: List[EthereumTransaction],
            with_limit: bool,
    ) -> List[EthereumTransaction]:
        if with_limit is False:
            return transactions

        transactions_queried_so_far = sum(x for _, x in self.tx_per_address.items())
        remaining_num_tx = FREE_ETH_TX_LIMIT - transactions_queried_so_far
        returning_tx_length = min(remaining_num_tx, len(transactions))
        # Note down how many we got for this address
        self.tx_per_address[address] = returning_tx_length
        return transactions[:returning_tx_length]

    def single_address_query_transactions(
            self,
            address: ChecksumEthAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
            with_limit: bool,
            only_cache: bool,
    ) -> List[EthereumTransaction]:
        self.tx_per_address[address] = 0
        transactions = self.database.get_ethereum_transactions(
            from_ts=start_ts,
            to_ts=end_ts,
            address=address,
        )
        if only_cache:
            return self._return_transactions_maybe_limit(
                address=address,
                transactions=transactions,
                with_limit=with_limit,
            )

        ranges = DBQueryRanges(self.database)
        ranges_to_query = ranges.get_location_query_ranges(
            location_string=f'ethtxs_{address}',
            start_ts=start_ts,
            end_ts=end_ts,
        )
        new_transactions = []
        for query_start_ts, query_end_ts in ranges_to_query:
            for internal in (False, True):
                try:
                    new_transactions.extend(self.etherscan.get_transactions(
                        account=address,
                        internal=internal,
                        from_ts=query_start_ts,
                        to_ts=query_end_ts,
                    ))
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Got error "{str(e)}" while querying ethereum transactions '
                        f'from Etherscan. Transactions not added to the DB '
                        f'from_ts: {query_start_ts} '
                        f'to_ts: {query_end_ts} '
                        f'internal: {internal}',
                    )

        # add new transactions to the DB
        if new_transactions != []:
            self.database.add_ethereum_transactions(new_transactions, from_etherscan=True)
            # And since at least for now the increasingly negative nonce for the internal
            # transactions happens only in the DB writing, requery the entire batch from
            # the DB to get the updated transactions
            transactions = self.database.get_ethereum_transactions(
                from_ts=start_ts,
                to_ts=end_ts,
                address=address,
            )

        # and also set the last queried timestamps for the address
        ranges.update_used_query_range(
            location_string=f'ethtxs_{address}',
            start_ts=start_ts,
            end_ts=end_ts,
            ranges_to_query=ranges_to_query,
        )

        return self._return_transactions_maybe_limit(
            address=address,
            transactions=transactions,
            with_limit=with_limit,
        )

    @protect_with_lock()
    def query(
            self,
            addresses: Optional[List[ChecksumEthAddress]],
            from_ts: Timestamp,
            to_ts: Timestamp,
            with_limit: bool = False,
            recent_first: bool = False,
            only_cache: bool = False,
    ) -> List[EthereumTransaction]:
        """Queries for all transactions (normal AND internal) of all ethereum accounts.
        Returns a list of all transactions of all accounts sorted by time.

        If `with_limit` is true then the api limit is applied

        if `recent_first` is true then the transactions are returned with the most
        recent first on the list

        May raise:
        - RemoteError if etherscan is used and there is a problem with reaching it or
        with parsing the response.
        """
        transactions_set: Set[EthereumTransaction] = set()

        if addresses is not None:
            accounts = addresses
        else:
            accounts = self.database.get_blockchain_accounts().eth

        for address in accounts:
            new_transactions = self.single_address_query_transactions(
                address=address,
                start_ts=from_ts,
                end_ts=to_ts,
                with_limit=with_limit,
                only_cache=only_cache,
            )
            transactions_set.update(set(new_transactions))

        transactions = list(transactions_set)
        transactions.sort(key=lambda tx: tx.timestamp, reverse=recent_first)
        return transactions
