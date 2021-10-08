import logging
from collections import defaultdict
from typing import TYPE_CHECKING, DefaultDict, List, Optional, Tuple

from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.db.filtering import ETHTransactionsFilterQuery
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.errors import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import ChecksumEthAddress, EthereumTransaction, Timestamp
from rotkehlchen.utils.misc import hexstring_to_bytes, ts_now
from rotkehlchen.utils.mixins.lockable import LockableQueryMixIn, protect_with_lock

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt
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

    def reset_count(self) -> None:
        """Reset the limit counter for ethereum transactions

        This should be done by the frontend for non-premium users at the start
        of any batch of transaction queries.
        """
        self.ethereum.tx_per_address = defaultdict(int)

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
            self.ethereum.tx_per_address[address] = count

        if requested_addresses is not None:
            transactions_for_other_addies = sum(x for addy, x in self.ethereum.tx_per_address.items() if addy not in requested_addresses)  # noqa: E501
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
            try:
                new_transactions.extend(self.ethereum.etherscan.get_transactions(
                    account=address,
                    from_ts=query_start_ts,
                    to_ts=query_end_ts,
                ))
            except RemoteError as e:
                self.ethereum.msg_aggregator.add_error(
                    f'Got error "{str(e)}" while querying ethereum transactions '
                    f'from Etherscan. Transactions not added to the DB '
                    f'from_ts: {query_start_ts} '
                    f'to_ts: {query_end_ts} ',
                )

        # add new transactions to the DB
        if new_transactions != []:
            dbethtx.add_ethereum_transactions(new_transactions)

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
    ) -> Tuple[List[EthereumTransaction], int]:
        """Queries for all transactions (normal AND internal) of an ethereum
        address or of all addresses.
        Returns a list of all transactions filtered and sorted according to the parameters.

        If `with_limit` is true then the api limit is applied

        if `recent_first` is true then the transactions are returned with the most
        recent first on the list

        May raise:
        - RemoteError if etherscan is used and there is a problem with reaching it or
        with parsing the response.
        - pysqlcipher3.dbapi2.OperationalError if the SQL query fails due to
        invalid filtering arguments.
        """
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
        transactions, total_filter_count = dbethtx.get_ethereum_transactions(filter_=filter_query)
        return (
            self._return_transactions_maybe_limit(
                requested_addresses=query_addresses,
                transactions=transactions,
                with_limit=with_limit,
            ),
            total_filter_count,
        )

    def get_or_query_transaction_receipt(
            self,
            tx_hash: str,
    ) -> Optional['EthereumTxReceipt']:
        """
        Gets the receipt from the DB if it exist. If not queries the chain for it,
        saves it in the DB and then returns it.

        Also if the actual transaction does not exist in the DB it queries it and saves it there.

        May raise:

        - DeserializationError
        - RemoteError
        """
        tx_hash_b = hexstring_to_bytes(tx_hash)
        dbethtx = DBEthTx(self.database)
        # If the transaction is not in the DB then query it and add it
        result, _ = dbethtx.get_ethereum_transactions(ETHTransactionsFilterQuery.make(tx_hash=tx_hash_b))  # noqa: E501
        if len(result) == 0:
            transaction = self.ethereum.get_transaction_by_hash(tx_hash)
            if transaction is None:
                return None  # hash does not correspond to a transaction

            dbethtx.add_ethereum_transactions([transaction])

        tx_receipt = dbethtx.get_receipt(tx_hash_b)
        if tx_receipt is not None:
            return tx_receipt

        # not in the DB, so we need to query the chain for it
        tx_receipt_data = self.ethereum.get_transaction_receipt(tx_hash=tx_hash)
        dbethtx.add_receipt_data(tx_receipt_data)
        tx_receipt = dbethtx.get_receipt(tx_hash_b)
        return tx_receipt
