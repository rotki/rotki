import logging
from collections import defaultdict
from typing import TYPE_CHECKING, List, Optional, Tuple

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

    def single_address_query_transactions(
            self,
            address: ChecksumEthAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> None:
        """Only queries new transactions and adds them to the DB

        This is our attempt to identify as many transactions related to the address
        as possible. This unfortunately at the moment depends on etherscan as it's
        the only open indexing service for "appearances" of an address.

        Trueblocks ... we need you.
        """
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
                    action='txlist',
                ))
            except RemoteError as e:
                self.ethereum.msg_aggregator.add_error(
                    f'Got error "{str(e)}" while querying ethereum transactions '
                    f'from Etherscan. Transactions not added to the DB '
                    f'address: {address} '
                    f'from_ts: {query_start_ts} '
                    f'to_ts: {query_end_ts} ',
                )

        # add new transactions to the DB
        if new_transactions != []:
            dbethtx.add_ethereum_transactions(new_transactions, relevant_address=address)

        # and now internal transactions, after normal ones so they are already in DB
        new_internal_txs = []
        for query_start_ts, query_end_ts in ranges_to_query:
            try:
                new_internal_txs.extend(self.ethereum.etherscan.get_transactions(
                    account=address,
                    from_ts=query_start_ts,
                    to_ts=query_end_ts,
                    action='txlistinternal',
                ))
            except RemoteError as e:
                self.ethereum.msg_aggregator.add_error(
                    f'Got error "{str(e)}" while querying internal ethereum transactions '
                    f'from Etherscan. Transactions not added to the DB '
                    f'address: {address} '
                    f'from_ts: {query_start_ts} '
                    f'to_ts: {query_end_ts} ',
                )

        # add new internal transactions to the DB
        if new_internal_txs != []:
            for internal_tx in new_internal_txs:
                # make sure all internal transaction parent transactions are in the DB
                result = dbethtx.get_ethereum_transactions(
                    ETHTransactionsFilterQuery.make(tx_hash=internal_tx.parent_tx_hash),
                    has_premium=True,  # ignore limiting here
                )
                if len(result) != 0:
                    continue  # already got that transaction

                txhash = '0x' + internal_tx.parent_tx_hash.hex()
                transaction = self.ethereum.get_transaction_by_hash(txhash)
                if transaction is None:
                    continue  # hash does not correspond to a transaction
                # add the parent transaction to the DB
                dbethtx.add_ethereum_transactions([transaction], relevant_address=address)

            # add all new internal txs to the DB
            dbethtx.add_ethereum_internal_transactions(new_internal_txs, relevant_address=address)

        # and now detect ERC20 events thanks to etherscan and get their transactions
        erc20_tx_hashes = set()
        for query_start_ts, query_end_ts in ranges_to_query:
            try:
                erc20_tx_hashes.update(self.ethereum.etherscan.get_transactions(
                    account=address,
                    from_ts=query_start_ts,
                    to_ts=query_end_ts,
                    action='tokentx',
                ))
            except RemoteError as e:
                self.ethereum.msg_aggregator.add_error(
                    f'Got error "{str(e)}" while querying token transactions'
                    f'from Etherscan. Transactions not added to the DB '
                    f'address: {address} '
                    f'from_ts: {query_start_ts} '
                    f'to_ts: {query_end_ts} ',
                )

        # and add them to the DB
        for tx_hash in erc20_tx_hashes:
            result = dbethtx.get_ethereum_transactions(
                ETHTransactionsFilterQuery.make(tx_hash=tx_hash),
                has_premium=True,  # ignore limiting here
            )
            if len(result) != 0:
                continue  # already got that transaction

            transaction = self.ethereum.get_transaction_by_hash(tx_hash)
            if transaction is None:
                continue  # hash does not correspond to a transaction

            dbethtx.add_ethereum_transactions([transaction], relevant_address=address)

        # finally also set the last queried timestamps for the address
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
            has_premium: bool = False,
            only_cache: bool = False,
    ) -> Tuple[List[EthereumTransaction], int]:
        """Queries for all transactions of an ethereum address or of all addresses.

        Returns a list of all transactions filtered and sorted according to the parameters.

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
        return dbethtx.get_ethereum_transactions_and_limit_info(
            filter_=filter_query,
            has_premium=has_premium,
        )

    def get_or_query_transaction_receipt(
            self,
            tx_hash: str,
    ) -> Optional['EthereumTxReceipt']:
        """
        Gets the receipt from the DB if it exists. If not queries the chain for it,
        saves it in the DB and then returns it.

        Also if the actual transaction does not exist in the DB it queries it and saves it there.

        May raise:

        - DeserializationError
        - RemoteError
        """
        tx_hash_b = hexstring_to_bytes(tx_hash)
        dbethtx = DBEthTx(self.database)
        # If the transaction is not in the DB then query it and add it
        result = dbethtx.get_ethereum_transactions(
            filter_=ETHTransactionsFilterQuery.make(tx_hash=tx_hash_b),
            has_premium=True,  # we don't need any limiting here
        )
        if len(result) == 0:
            transaction = self.ethereum.get_transaction_by_hash(tx_hash)
            if transaction is None:
                return None  # hash does not correspond to a transaction

            dbethtx.add_ethereum_transactions([transaction], relevant_address=None)

        tx_receipt = dbethtx.get_receipt(tx_hash_b)
        if tx_receipt is not None:
            return tx_receipt

        # not in the DB, so we need to query the chain for it
        tx_receipt_data = self.ethereum.get_transaction_receipt(tx_hash=tx_hash)
        dbethtx.add_receipt_data(tx_receipt_data)
        tx_receipt = dbethtx.get_receipt(tx_hash_b)
        return tx_receipt
