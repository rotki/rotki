import logging
from collections import defaultdict
from typing import TYPE_CHECKING, DefaultDict, Dict, List, Optional

from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.db.filtering import ETHTransactionsFilterQuery
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.errors import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import ChecksumEthAddress, EthereumTransaction, Timestamp
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.mixins.lockable import LockableQueryMixIn, protect_with_lock

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

FREE_ETH_TX_LIMIT = 250


class EthTransactions(LockableQueryMixIn):

    def __init__(
            self,
            ethereum: 'EthereumManager',
            database: 'DBHandler',
    ) -> None:
        super().__init__()
        self.ethereum = ethereum
        self.database = database
        self.tx_per_address: Dict[ChecksumEthAddress, int] = defaultdict(int)

    def reset_count(self) -> None:
        """Reset the limit counter for ethereum transactions

        This should be done by the frontend for non-premium users at the start
        of any batch of transaction queries.
        """
        self.tx_per_address = defaultdict(int)

    def _return_transactions_maybe_limit(
            self,
            requested_addresses: Optional[List[ChecksumEthAddress]],
            transactions: List[EthereumTransaction],
            with_limit: bool,
    ) -> List[EthereumTransaction]:
        if with_limit is False:
            return transactions

        count_map: DefaultDict[ChecksumEthAddress, int] = defaultdict(int)
        for tx in transactions:
            count_map[tx.from_address] += 1

        for address, count in count_map.items():
            self.tx_per_address[address] = count

        if requested_addresses is not None:
            transactions_for_other_addies = sum(x for addy, x in self.tx_per_address.items() if addy not in requested_addresses)  # noqa: E501
            remaining_num_tx = FREE_ETH_TX_LIMIT - transactions_for_other_addies
            returning_tx_length = min(remaining_num_tx, len(transactions))
        else:
            returning_tx_length = min(FREE_ETH_TX_LIMIT, len(transactions))

        return transactions[:returning_tx_length]

    def single_address_query_transactions(
            self,
            address: ChecksumEthAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> None:
        """Only queries new transactions and adds them to the DB"""
        ranges = DBQueryRanges(self.database)
        ranges_to_query = ranges.get_location_query_ranges(
            location_string=f'ethtxs_{address}',
            start_ts=start_ts,
            end_ts=end_ts,
        )
        new_transactions = []
        dbethtx = DBEthTx(self.database)
        for query_start_ts, query_end_ts in ranges_to_query:
            for internal in (False, True):
                try:
                    new_transactions.extend(self.ethereum.etherscan.get_transactions(
                        account=address,
                        internal=internal,
                        from_ts=query_start_ts,
                        to_ts=query_end_ts,
                    ))
                except RemoteError as e:
                    self.ethereum.msg_aggregator.add_error(
                        f'Got error "{str(e)}" while querying ethereum transactions '
                        f'from Etherscan. Transactions not added to the DB '
                        f'from_ts: {query_start_ts} '
                        f'to_ts: {query_end_ts} '
                        f'internal: {internal}',
                    )

        # add new transactions to the DB
        if new_transactions != []:
            dbethtx.add_ethereum_transactions(new_transactions, from_etherscan=True)

        # and also set the last queried timestamps for the address
        ranges.update_used_query_range(
            location_string=f'ethtxs_{address}',
            start_ts=start_ts,
            end_ts=end_ts,
            ranges_to_query=ranges_to_query,
        )

    @protect_with_lock()
    def query(
            self,
            filter_query: ETHTransactionsFilterQuery,
            with_limit: bool = False,
            only_cache: bool = False,
    ) -> List[EthereumTransaction]:
        """Queries for all transactions (normal AND internal) of an ethereum
        address or of all addresses.
        Returns a list of all transactions filtered and sorted according to the parameters.

        If `with_limit` is true then the api limit is applied

        if `recent_first` is true then the transactions are returned with the most
        recent first on the list

        May raise:
        - RemoteError if etherscan is used and there is a problem with reaching it or
        with parsing the response.
        """
        # Reset the counter for each query. Makes it easier to cheat when querying each
        # address sep
        # self.tx_per_address = defaultdict(int)
        query_addresses = filter_query.addresses

        if query_addresses is not None:
            accounts = query_addresses
        else:
            accounts = self.database.get_blockchain_accounts().eth

        if only_cache is False:
            f_from_ts = filter_query.from_ts
            f_to_ts = filter_query.to_ts
            from_ts = Timestamp(0) if f_from_ts is None else f_from_ts
            to_ts = ts_now() if f_to_ts is None else f_to_ts
            for address in accounts:
                self.single_address_query_transactions(
                    address=address,
                    start_ts=from_ts,
                    end_ts=to_ts,
                )

        dbethtx = DBEthTx(self.database)
        transactions = dbethtx.get_ethereum_transactions(filter_=filter_query)
        return self._return_transactions_maybe_limit(
            requested_addresses=query_addresses,
            transactions=transactions,
            with_limit=with_limit,
        )
