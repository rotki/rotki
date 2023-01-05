import logging
from abc import ABCMeta
from collections import defaultdict
from contextlib import contextmanager
from typing import TYPE_CHECKING, Iterator, Optional

import gevent
from gevent.lock import Semaphore
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.api.websockets.typedefs import TransactionStatusStep, WSMessageType
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash, Timestamp, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.structures import EvmTxReceipt
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

    from .node_inquirer import EvmNodeInquirer


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EvmTransactions(metaclass=ABCMeta):  # noqa: B024

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            database: 'DBHandler',
    ) -> None:
        super().__init__()
        self.evm_inquirer = evm_inquirer
        self.database = database
        self.address_tx_locks: dict[ChecksumEvmAddress, Semaphore] = defaultdict(Semaphore)
        self.missing_receipts_lock = Semaphore()
        self.msg_aggregator = database.msg_aggregator

    @contextmanager
    def wait_until_no_query_for(self, addresses: list[ChecksumEvmAddress]) -> Iterator[None]:
        """Will acquire all locks relevant to an address and yield to the caller"""
        locks = []
        for address in addresses:
            lock = self.address_tx_locks[address]
            lock.acquire()
            locks.append(lock)

        yield  # yield to caller since all locks are now acquired

        for lock in locks:  # clean up
            lock.release()

    def single_address_query_transactions(
            self,
            address: ChecksumEvmAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> None:
        """Only queries new transactions and adds them to the DB

        This is our attempt to identify as many transactions related to the address
        as possible. This unfortunately at the moment depends on etherscan as it's
        the only open indexing service for "appearances" of an address.

        Trueblocks ... we need you.
        """
        lock = self.address_tx_locks[address]
        serialized_chain = self.evm_inquirer.blockchain.serialize()
        with lock:
            self.msg_aggregator.add_message(
                message_type=WSMessageType.ETHEREUM_TRANSACTION_STATUS,
                data={
                    'address': address,
                    'blockchain': serialized_chain,
                    'period': [start_ts, end_ts],
                    'status': str(TransactionStatusStep.QUERYING_TRANSACTIONS_STARTED),
                },
            )
            self._get_transactions_for_range(address=address, start_ts=start_ts, end_ts=end_ts)
            self._get_internal_transactions_for_ranges(
                address=address,
                start_ts=start_ts,
                end_ts=end_ts,
            )
            self._get_erc20_transfers_for_ranges(
                address=address,
                start_ts=start_ts,
                end_ts=end_ts,
            )
        self.msg_aggregator.add_message(
            message_type=WSMessageType.ETHEREUM_TRANSACTION_STATUS,
            data={
                'address': address,
                'blockchain': serialized_chain,
                'period': [start_ts, end_ts],
                'status': str(TransactionStatusStep.QUERYING_TRANSACTIONS_FINISHED),
            },
        )

    def query_chain(self, filter_query: EvmTransactionsFilterQuery) -> None:
        """Queries the chain (or a remote such as etherscan) for all transactions
        of an evm address or of all addresses. Will query for only the time requested
        in the filter and the part of that time that has not yet been queried.

        Saves the results in the database.

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
            with self.database.conn.read_ctx() as cursor:
                accounts = self.database.get_blockchain_accounts(cursor).get(
                    blockchain=self.evm_inquirer.blockchain,
                )

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

    def _get_transactions_for_range(
            self,
            address: ChecksumEvmAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> None:
        """Queries etherscan for all evm transactions of address in the given ranges.

        If any transactions are found, they are added in the DB
        """
        location_string = f'{self.evm_inquirer.blockchain.to_range_prefix("txs")}_{address}'
        ranges = DBQueryRanges(self.database)
        with self.database.conn.read_ctx() as cursor:
            ranges_to_query = ranges.get_location_query_ranges(
                cursor=cursor,
                location_string=location_string,
                start_ts=start_ts,
                end_ts=end_ts,
            )
        dbevmtx = DBEvmTx(self.database)

        for query_start_ts, query_end_ts in ranges_to_query:
            log.debug(f'Querying {self.evm_inquirer.chain_name} transactions for {address} -> {query_start_ts} - {query_end_ts}')  # noqa: E501
            try:
                for new_transactions in self.evm_inquirer.etherscan.get_transactions(
                    account=address,
                    from_ts=query_start_ts,
                    to_ts=query_end_ts,
                    action='txlist',
                ):
                    # add new transactions to the DB
                    if len(new_transactions) != 0:
                        with self.database.user_write() as cursor:
                            dbevmtx.add_evm_transactions(
                                write_cursor=cursor,
                                evm_transactions=new_transactions,
                                relevant_address=address,
                            )
                            # update last queried time for the address
                            ranges.update_used_query_range(
                                write_cursor=cursor,
                                location_string=location_string,
                                queried_ranges=[(query_start_ts, new_transactions[-1].timestamp)],
                            )

                        self.msg_aggregator.add_message(
                            message_type=WSMessageType.ETHEREUM_TRANSACTION_STATUS,
                            data={
                                'address': address,
                                'blockchain': self.evm_inquirer.chain_name,
                                'period': [query_start_ts, new_transactions[-1].timestamp],
                                'status': str(TransactionStatusStep.QUERYING_TRANSACTIONS),
                            },
                        )

            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Got error "{str(e)}" while querying {self.evm_inquirer.chain_name} '
                    f'transactions from Etherscan. Some transactions not added to the DB '
                    f'address: {address} '
                    f'from_ts: {query_start_ts} '
                    f'to_ts: {query_end_ts} ',
                )
                return

        log.debug(f'{self.evm_inquirer.chain_name} transactions done for {address}. Update range {start_ts} - {end_ts}')  # noqa: E501
        with self.database.user_write() as cursor:
            ranges.update_used_query_range(  # entire range is now considered queried
                write_cursor=cursor,
                location_string=location_string,
                queried_ranges=[(start_ts, end_ts)],
            )

    def _get_internal_transactions_for_ranges(
            self,
            address: ChecksumEvmAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> None:
        """Queries etherscan for all internal transactions of address in the given ranges.

        If any internal transactions are found, they are added in the DB
        """
        location_string = f'{self.evm_inquirer.blockchain.to_range_prefix("internaltxs")}_{address}'  # noqa: E501
        ranges = DBQueryRanges(self.database)
        dbevmtx = DBEvmTx(self.database)
        with self.database.conn.read_ctx() as cursor:
            ranges_to_query = ranges.get_location_query_ranges(
                cursor=cursor,
                location_string=location_string,
                start_ts=start_ts,
                end_ts=end_ts,
            )
        new_internal_txs = []
        for query_start_ts, query_end_ts in ranges_to_query:
            log.debug(f'Querying {self.evm_inquirer.chain_name} internal transactions for {address} -> {query_start_ts} - {query_end_ts}')  # noqa: E501
            try:
                for new_internal_txs in self.evm_inquirer.etherscan.get_transactions(
                    account=address,
                    from_ts=query_start_ts,
                    to_ts=query_end_ts,
                    action='txlistinternal',
                ):
                    if len(new_internal_txs) != 0:
                        with self.database.user_write() as cursor:
                            for internal_tx in new_internal_txs:
                                # make sure internal transaction parent transactions are in the DB
                                gevent.sleep(0)
                                result = dbevmtx.get_evm_transactions(
                                    cursor,
                                    EvmTransactionsFilterQuery.make(
                                        tx_hash=internal_tx.parent_tx_hash,
                                        chain_id=self.evm_inquirer.chain_id,
                                    ),
                                    has_premium=True,  # ignore limiting here
                                )
                                if len(result) == 0:  # parent transaction is not in the DB. Get it
                                    transaction = self.evm_inquirer.get_transaction_by_hash(internal_tx.parent_tx_hash)  # noqa: E501
                                    gevent.sleep(0)
                                    dbevmtx.add_evm_transactions(
                                        write_cursor=cursor,
                                        evm_transactions=[transaction],
                                        relevant_address=address,
                                    )
                                    timestamp = transaction.timestamp
                                else:
                                    timestamp = result[0].timestamp

                                dbevmtx.add_evm_internal_transactions(
                                    write_cursor=cursor,
                                    transactions=[internal_tx],
                                    relevant_address=address,
                                )
                                log.debug(f'Internal {self.evm_inquirer.chain_name} transactions for {address} -> update range {query_start_ts} - {timestamp}')  # noqa: E501
                                # update last queried time for address
                                ranges.update_used_query_range(
                                    write_cursor=cursor,
                                    location_string=location_string,
                                    queried_ranges=[(query_start_ts, timestamp)],
                                )

                            self.msg_aggregator.add_message(
                                message_type=WSMessageType.ETHEREUM_TRANSACTION_STATUS,
                                data={
                                    'address': address,
                                    'blockchain': self.evm_inquirer.chain_name,
                                    'period': [query_start_ts, timestamp],
                                    'status': str(TransactionStatusStep.QUERYING_INTERNAL_TRANSACTIONS),  # noqa: E501
                                },
                            )

            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Got error "{str(e)}" while querying internal {self.evm_inquirer.chain_name} '
                    f'transactions from Etherscan. Transactions not added to the DB '
                    f'address: {address} '
                    f'from_ts: {query_start_ts} '
                    f'to_ts: {query_end_ts} ',
                )
                return

        log.debug(f'Internal {self.evm_inquirer.chain_name} transactions for address {address} done. Update range {start_ts} - {end_ts}')  # noqa: E501
        with self.database.user_write() as cursor:
            ranges.update_used_query_range(  # entire range is now considered queried
                write_cursor=cursor,
                location_string=location_string,
                queried_ranges=[(start_ts, end_ts)],
            )

    def _get_erc20_transfers_for_ranges(
            self,
            address: ChecksumEvmAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> None:
        """Queries etherscan for all erc20 transfers of address in the given ranges.

        If any transfers are found, they are added in the DB
        """
        location_string = f'{self.evm_inquirer.blockchain.to_range_prefix("tokentxs")}_{address}'
        dbevmtx = DBEvmTx(self.database)
        ranges = DBQueryRanges(self.database)
        with self.database.conn.read_ctx() as cursor:
            ranges_to_query = ranges.get_location_query_ranges(
                cursor=cursor,
                location_string=location_string,
                start_ts=start_ts,
                end_ts=end_ts,
            )

        for query_start_ts, query_end_ts in ranges_to_query:
            log.debug(f'Querying {self.evm_inquirer.chain_name} ERC20 Transfers for {address} -> {query_start_ts} - {query_end_ts}')  # noqa: E501
            try:
                for erc20_tx_hashes in self.evm_inquirer.etherscan.get_token_transaction_hashes(
                    account=address,
                    from_ts=query_start_ts,
                    to_ts=query_end_ts,
                ):
                    with self.database.user_write() as cursor:
                        for tx_hash in erc20_tx_hashes:
                            tx_hash_bytes = deserialize_evm_tx_hash(tx_hash)
                            result = dbevmtx.get_evm_transactions(
                                cursor,
                                EvmTransactionsFilterQuery.make(tx_hash=tx_hash_bytes, chain_id=self.evm_inquirer.chain_id),  # noqa: E501
                                has_premium=True,  # ignore limiting here
                            )
                            if len(result) == 0:  # if transaction is not there add it
                                gevent.sleep(0)
                                transaction = self.evm_inquirer.get_transaction_by_hash(tx_hash_bytes)  # noqa: E501
                                dbevmtx.add_evm_transactions(
                                    write_cursor=cursor,
                                    evm_transactions=[transaction],
                                    relevant_address=address,
                                )
                                timestamp = transaction.timestamp
                            else:
                                timestamp = result[0].timestamp

                            log.debug(f'{self.evm_inquirer.chain_name} ERC20 Transfers for {address} -> update range {query_start_ts} - {timestamp}')  # noqa: E501
                            # update last queried time for the address
                            ranges.update_used_query_range(
                                write_cursor=cursor,
                                location_string=location_string,
                                queried_ranges=[(query_start_ts, timestamp)],
                            )

                            self.msg_aggregator.add_message(
                                message_type=WSMessageType.ETHEREUM_TRANSACTION_STATUS,
                                data={
                                    'address': address,
                                    'blockchain': self.evm_inquirer.chain_name,
                                    'period': [query_start_ts, timestamp],
                                    'status': str(TransactionStatusStep.QUERYING_ETHEREUM_TOKENS_TRANSACTIONS),  # noqa: E501
                                },
                            )
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Got error "{str(e)}" while querying {self.evm_inquirer.chain_name} '
                    f'token transactions from Etherscan. Transactions not added to the DB '
                    f'address: {address} '
                    f'from_ts: {query_start_ts} '
                    f'to_ts: {query_end_ts} ',
                )

        log.debug(f'{self.evm_inquirer.chain_name} ERC20 Transfers done for address {address}. Update range {start_ts} - {end_ts}')  # noqa: E501
        with self.database.user_write() as cursor:
            ranges.update_used_query_range(  # entire range is now considered queried
                write_cursor=cursor,
                location_string=location_string,
                queried_ranges=[(start_ts, end_ts)],
            )

    def get_or_query_transaction_receipt(
            self,
            write_cursor: 'DBCursor',
            tx_hash: EVMTxHash,
    ) -> 'EvmTxReceipt':
        """
        Gets the receipt from the DB if it exists. If not queries the chain for it,
        saves it in the DB and then returns it.

        Also if the actual transaction does not exist in the DB it queries it and saves it there.

        May raise:

        - DeserializationError
        - RemoteError if the transaction hash can't be found in any of the connected nodes
        """
        dbevmtx = DBEvmTx(self.database)
        # If the transaction is not in the DB then query it and add it
        result = dbevmtx.get_evm_transactions(
            cursor=write_cursor,
            filter_=EvmTransactionsFilterQuery.make(tx_hash=tx_hash, chain_id=self.evm_inquirer.chain_id),  # noqa: E501
            has_premium=True,  # we don't need any limiting here
        )

        if len(result) == 0:
            transaction = self.evm_inquirer.get_transaction_by_hash(tx_hash)
            dbevmtx.add_evm_transactions(write_cursor, [transaction], relevant_address=None)
            self._get_internal_transactions_for_ranges(
                address=transaction.from_address,
                start_ts=transaction.timestamp,
                end_ts=transaction.timestamp,
            )
            self._get_erc20_transfers_for_ranges(
                address=transaction.from_address,
                start_ts=transaction.timestamp,
                end_ts=transaction.timestamp,
            )

        tx_receipt = dbevmtx.get_receipt(
            cursor=write_cursor,
            tx_hash=tx_hash,
            chain_id=self.evm_inquirer.chain_id,
        )
        if tx_receipt is not None:
            return tx_receipt

        # not in the DB, so we need to query the chain for it
        tx_receipt_data = self.evm_inquirer.get_transaction_receipt(tx_hash=tx_hash)
        try:
            dbevmtx.add_receipt_data(
                write_cursor=write_cursor,
                chain_id=self.evm_inquirer.chain_id,
                data=tx_receipt_data,
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            if 'UNIQUE constraint failed: evmtx_receipts.tx_hash' not in str(e):
                raise  # otherwise something else added the receipt before so we just continue
        tx_receipt = dbevmtx.get_receipt(
            cursor=write_cursor,
            tx_hash=tx_hash,
            chain_id=self.evm_inquirer.chain_id,
        )

        return tx_receipt  # type: ignore  # tx_receipt was just added in the DB so should be there  # noqa: E501

    def get_receipts_for_transactions_missing_them(
            self,
            limit: Optional[int] = None,
            addresses: Optional[list[ChecksumEvmAddress]] = None,
    ) -> None:
        """
        Searches the database for up to `limit` transactions that have no corresponding receipt
        and for each one of them queries the receipt and saves it in the DB.

        It's protected by a lock to not enter the same code twice
        (i.e. from periodic tasks and from pnl report history events gathering)

        If the addresses argument is provided then it is used to filter the transactions missing
        their receipt. If it is None then no distinction is made among the transactions.
        """
        with self.missing_receipts_lock:
            dbevmtx = DBEvmTx(self.database)
            with self.database.conn.read_ctx() as cursor:
                if addresses is None:
                    tx_filter_query = None
                else:
                    tx_filter_query = EvmTransactionsFilterQuery.make(
                        addresses=addresses,
                    )

                hash_results = dbevmtx.get_transaction_hashes_no_receipt(
                    tx_filter_query=tx_filter_query,
                    limit=limit,
                )

            if len(hash_results) == 0:
                return  # nothing to do

            with self.database.user_write() as cursor:
                for entry in hash_results:
                    try:
                        tx_receipt_data = self.evm_inquirer.get_transaction_receipt(tx_hash=entry)
                    except RemoteError as e:
                        self.msg_aggregator.add_warning(f'Failed to query information for {self.evm_inquirer.chain_name} transaction {entry.hex()} due to {str(e)}. Skipping...')  # noqa: E501
                        continue

                    try:
                        dbevmtx.add_receipt_data(
                            write_cursor=cursor,
                            chain_id=self.evm_inquirer.chain_id,
                            data=tx_receipt_data,
                        )
                    except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                        if 'UNIQUE constraint failed: evmtx_receipts.tx_hash' not in str(e):
                            log.error(f'Fialed to store transaction {entry.hex()} receipt due to {str(e)}')  # noqa: E501
                            raise  # if receipt is already added by other greenlet it's fine
