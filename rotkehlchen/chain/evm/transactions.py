import logging
from abc import ABCMeta
from collections import defaultdict
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Optional

from gevent.lock import Semaphore

from rotkehlchen.api.websockets.typedefs import TransactionStatusStep, WSMessageType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.constants import GENESIS_HASH
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.types import EvmAccount
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import AlreadyExists, InputError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import SPAM_PROTOCOL, ChecksumEvmAddress, EvmTokenKind, EVMTxHash, Timestamp
from rotkehlchen.utils.hexbytes import hexstring_to_bytes
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceipt
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.types import EvmTransaction


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
        self.dbranges = DBQueryRanges(self.database)
        self.address_tx_locks: dict[ChecksumEvmAddress, Semaphore] = defaultdict(Semaphore)
        self.missing_receipts_lock = Semaphore()
        self.msg_aggregator = database.msg_aggregator
        self.dbevmtx = DBEvmTx(database)

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
        serialized_chain_id = self.evm_inquirer.chain_id.to_name()
        with lock:
            self.msg_aggregator.add_message(
                message_type=WSMessageType.EVM_TRANSACTION_STATUS,
                data={
                    'address': address,
                    'evm_chain': serialized_chain_id,
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
            message_type=WSMessageType.EVM_TRANSACTION_STATUS,
            data={
                'address': address,
                'evm_chain': serialized_chain_id,
                'period': [start_ts, end_ts],
                'status': str(TransactionStatusStep.QUERYING_TRANSACTIONS_FINISHED),
            },
        )

    def query_chain(self, filter_query: EvmTransactionsFilterQuery) -> None:
        """Queries the chain (or a remote such as etherscan) for all transactions of an evm address
        or of all addresses. Will query only addresses of the filter with same chain_id as this
        class and query only the time requested in the filter and the part of that time that has
        not yet been queried.

        Saves the results in the database.

        May raise:
        - RemoteError if etherscan is used and there is a problem with reaching it or
        with parsing the response.
        - pysqlcipher3.dbapi2.OperationalError if the SQL query fails due to
        invalid filtering arguments.
        """
        query_accounts = filter_query.accounts
        if query_accounts is not None:
            accounts = tuple(x.address for x in query_accounts if x.chain_id == self.evm_inquirer.chain_id)  # noqa: E501
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
        self.get_chain_specific_multiaddress_data(accounts, from_ts, to_ts)

    def _query_and_save_transactions_for_range(
            self,
            address: ChecksumEvmAddress,
            period: TimestampOrBlockRange,
            location_string: str | None = None,
    ) -> None:
        """Helper function to abstract tx querying functionality for different range types"""
        for new_transactions in self.evm_inquirer.etherscan.get_transactions(
                account=address,
                action='txlist',
                period_or_hash=period,
        ):
            # add new transactions to the DB
            if len(new_transactions) == 0:
                continue

            with self.database.user_write() as write_cursor:
                self.dbevmtx.add_evm_transactions(
                    write_cursor=write_cursor,
                    evm_transactions=new_transactions,
                    relevant_address=address,
                )
            if period.range_type == 'timestamps':
                assert location_string, 'should always be given for timestamps'
                with self.database.user_write() as write_cursor:
                    # update last queried time for the address
                    self.dbranges.update_used_query_range(
                        write_cursor=write_cursor,
                        location_string=location_string,
                        queried_ranges=[(period.from_value, new_transactions[-1].timestamp)],  # type: ignore
                    )

                self.msg_aggregator.add_message(
                    message_type=WSMessageType.EVM_TRANSACTION_STATUS,
                    data={
                        'address': address,
                        'evm_chain': self.evm_inquirer.chain_id.to_name(),
                        'period': [period.from_value, new_transactions[-1].timestamp],
                        'status': str(TransactionStatusStep.QUERYING_TRANSACTIONS),
                    },
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
        with self.database.conn.read_ctx() as cursor:
            ranges_to_query = self.dbranges.get_location_query_ranges(
                cursor=cursor,
                location_string=location_string,
                start_ts=start_ts,
                end_ts=end_ts,
            )
        for query_start_ts, query_end_ts in ranges_to_query:
            log.debug(f'Querying {self.evm_inquirer.chain_name} transactions for {address} -> {query_start_ts} - {query_end_ts}')  # noqa: E501
            try:
                self._query_and_save_transactions_for_range(
                    address=address,
                    period=TimestampOrBlockRange(
                        range_type='timestamps',
                        from_value=query_start_ts,
                        to_value=query_end_ts,
                    ),
                    location_string=location_string,
                )

            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Got error "{e!s}" while querying {self.evm_inquirer.chain_name} '
                    f'transactions from Etherscan. Some transactions not added to the DB '
                    f'address: {address} '
                    f'from_ts: {query_start_ts} '
                    f'to_ts: {query_end_ts} ',
                )
                return

        log.debug(f'{self.evm_inquirer.chain_name} transactions done for {address}. Update range {start_ts} - {end_ts}')  # noqa: E501
        with self.database.user_write() as cursor:
            self.dbranges.update_used_query_range(  # entire range is now considered queried
                write_cursor=cursor,
                location_string=location_string,
                queried_ranges=[(start_ts, end_ts)],
            )

    def _query_and_save_internal_transactions_for_range_or_parent_hash(
            self,
            address: ChecksumEvmAddress | None,
            period_or_hash: TimestampOrBlockRange | EVMTxHash,
            location_string: str | None = None,
    ) -> None:
        """Helper function to abstract internal tx querying for different range types
        or for a specific parent transaction hash.

        If address is None, then etherscan query will return all internal transactions.
        """
        for new_internal_txs in self.evm_inquirer.etherscan.get_transactions(
                account=address,
                period_or_hash=period_or_hash,
                action='txlistinternal',
        ):
            if len(new_internal_txs) == 0:
                continue

            for internal_tx in new_internal_txs:
                if internal_tx.value == 0:
                    continue  # Only reason we need internal is for ether transfer. Ignore 0
                # make sure internal transaction parent transactions are in the DB
                with self.database.conn.read_ctx() as cursor:
                    tx, _ = self.get_or_create_transaction(
                        cursor=cursor,
                        tx_hash=internal_tx.parent_tx_hash,
                        relevant_address=address,
                    )
                    timestamp = tx.timestamp

                with self.database.conn.write_ctx() as write_cursor:
                    self.dbevmtx.add_evm_internal_transactions(
                        write_cursor=write_cursor,
                        transactions=[internal_tx],
                        relevant_address=None,  # no need to re-associate address
                    )
                if isinstance(period_or_hash, TimestampOrBlockRange) and period_or_hash.range_type == 'timestamps':  # noqa: E501
                    assert location_string, 'should always be given for timestamps'
                    log.debug(f'Internal {self.evm_inquirer.chain_name} transactions for {address} -> update range {period_or_hash.from_value} - {timestamp}')  # noqa: E501
                    with self.database.conn.write_ctx() as write_cursor:
                        # update last queried time for address
                        self.dbranges.update_used_query_range(
                            write_cursor=write_cursor,
                            location_string=location_string,
                            queried_ranges=[(period_or_hash.from_value, timestamp)],  # type: ignore
                        )

                    self.msg_aggregator.add_message(
                        message_type=WSMessageType.EVM_TRANSACTION_STATUS,
                        data={
                            'address': address,
                            'evm_chain': self.evm_inquirer.chain_id.to_name(),
                            'period': [period_or_hash.from_value, timestamp],
                            'status': str(TransactionStatusStep.QUERYING_INTERNAL_TRANSACTIONS),
                        },
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
        with self.database.conn.read_ctx() as cursor:
            ranges_to_query = self.dbranges.get_location_query_ranges(
                cursor=cursor,
                location_string=location_string,
                start_ts=start_ts,
                end_ts=end_ts,
            )
        for query_start_ts, query_end_ts in ranges_to_query:
            log.debug(f'Querying {self.evm_inquirer.chain_name} internal transactions for {address} -> {query_start_ts} - {query_end_ts}')  # noqa: E501
            try:
                self._query_and_save_internal_transactions_for_range_or_parent_hash(
                    address=address,
                    period_or_hash=TimestampOrBlockRange(
                        range_type='timestamps',
                        from_value=query_start_ts,
                        to_value=query_end_ts,
                    ),
                    location_string=location_string,
                )
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Got error "{e!s}" while querying internal {self.evm_inquirer.chain_name} '
                    f'transactions from Etherscan. Transactions not added to the DB '
                    f'address: {address} '
                    f'from_ts: {query_start_ts} '
                    f'to_ts: {query_end_ts} ',
                )
                return

        log.debug(f'Internal {self.evm_inquirer.chain_name} transactions for address {address} done. Update range {start_ts} - {end_ts}')  # noqa: E501
        with self.database.user_write() as cursor:
            self.dbranges.update_used_query_range(  # entire range is now considered queried
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
        with self.database.conn.read_ctx() as cursor:
            ranges_to_query = self.dbranges.get_location_query_ranges(
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
                    for tx_hash in erc20_tx_hashes:
                        with self.database.conn.read_ctx() as cursor:
                            tx, _ = self.get_or_create_transaction(
                                cursor=cursor,
                                tx_hash=tx_hash,
                                relevant_address=address,
                            )
                        timestamp = tx.timestamp
                        log.debug(f'{self.evm_inquirer.chain_name} ERC20 Transfers for {address} -> update range {query_start_ts} - {timestamp}')  # noqa: E501
                        with self.database.user_write() as write_cursor:
                            # update last queried time for the address
                            self.dbranges.update_used_query_range(
                                write_cursor=write_cursor,
                                location_string=location_string,
                                queried_ranges=[(query_start_ts, timestamp)],
                            )

                        self.msg_aggregator.add_message(
                            message_type=WSMessageType.EVM_TRANSACTION_STATUS,
                            data={
                                'address': address,
                                'evm_chain': self.evm_inquirer.chain_id.to_name(),
                                'period': [query_start_ts, timestamp],
                                'status': str(TransactionStatusStep.QUERYING_EVM_TOKENS_TRANSACTIONS),  # noqa: E501
                            },
                        )
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Got error "{e!s}" while querying {self.evm_inquirer.chain_name} '
                    f'token transactions from Etherscan. Transactions not added to the DB '
                    f'address: {address} '
                    f'from_ts: {query_start_ts} '
                    f'to_ts: {query_end_ts} ',
                )

        log.debug(f'{self.evm_inquirer.chain_name} ERC20 Transfers done for address {address}. Update range {start_ts} - {end_ts}')  # noqa: E501
        with self.database.user_write() as write_cursor:
            self.dbranges.update_used_query_range(  # entire range is now considered queried
                write_cursor=write_cursor,
                location_string=location_string,
                queried_ranges=[(start_ts, end_ts)],
            )

    def address_has_been_spammed(self, address: ChecksumEvmAddress) -> bool:
        """
        Queries erc20 tranfers for the given address and if it has only transfer of spam assets
        or ignored assets we return True. Stop at the first valid ERC20 transfer we find to exit
        as early as possible. If any transfer had an unknown asset mark the address as not spammed
        since we can't do more to classify it.
        """
        start_ts, end_ts = Timestamp(0), ts_now()
        checked_tokens = set()
        with self.database.conn.read_ctx() as cursor:
            ignored_assets = self.database.get_ignored_asset_ids(cursor)

        log.debug(f'Address detection: querying {self.evm_inquirer.chain_name} ERC20 Transfers for {address} -> {start_ts} - {end_ts}')  # noqa: E501
        try:
            for erc20_tx_hashes in self.evm_inquirer.etherscan.get_token_transaction_hashes(
                account=address,
                from_ts=start_ts,
                to_ts=end_ts,
            ):
                for tx_hash in erc20_tx_hashes:
                    raw_receipt_data = self.evm_inquirer.get_transaction_receipt(tx_hash)
                    for log_entry in raw_receipt_data['logs']:
                        if len(log_entry['topics']) == 0:
                            continue

                        topic_raw = log_entry['topics'][0]
                        try:
                            topic = hexstring_to_bytes(topic_raw)
                        except DeserializationError as e:
                            log.error(f'Failed to read topic {topic_raw} for a transaction receipt at {ts_now!r}. {e!s}. Skipping')  # noqa: E501
                            continue

                        if topic != ERC20_OR_ERC721_TRANSFER:
                            continue

                        log_address = deserialize_evm_address(log_entry['address'])
                        if log_address in checked_tokens:
                            continue

                        identifier = evm_address_to_identifier(
                            address=log_address,
                            chain_id=self.evm_inquirer.chain_id,
                            token_type=EvmTokenKind.ERC20,
                        )

                        if identifier in ignored_assets:
                            checked_tokens.add(log_address)
                            continue

                        try:
                            token = EvmToken(identifier)
                        except UnknownAsset:
                            return False

                        if token.protocol == SPAM_PROTOCOL:
                            checked_tokens.add(log_address)
                            continue

                        # this token is not ignored, is not spam and exists in the database
                        return False

                    log.debug(f'Address detection: queried {self.evm_inquirer.chain_name} ERC20 Transfers for {address} -> range {start_ts} - {end_ts}')  # noqa: E501
        except RemoteError as e:
            self.msg_aggregator.add_error(
                f'Got error "{e!s}" while querying {self.evm_inquirer.chain_name} '
                f'token transactions from Etherscan. address: {address} spam detection failed',
            )
            return False

        return True

    def ensure_tx_data_exists(
            self,
            cursor: 'DBCursor',
            tx_hash: 'EVMTxHash',
            relevant_address: Optional['ChecksumEvmAddress'],
    ) -> tuple[tuple[Any, ...], 'EvmTxReceipt']:
        """Makes sure that the required data for the transaction are in the database.
        If not, pulls them and stores them. For most chains this is the transaction and the
        receipt. Can be extended by subclasses for chain-specific information.

        May raise:
        - RemoteError if there is a problem querying the data sources or transaction hash does
        not exist.
        """
        query, bindings = EvmTransactionsFilterQuery.make(tx_hash=tx_hash, chain_id=self.evm_inquirer.chain_id).prepare()  # noqa: E501
        query, bindings = self.dbevmtx._form_evm_transaction_dbquery(query=query, bindings=bindings, has_premium=True)  # noqa: E501
        tx_data = cursor.execute(query, bindings).fetchone()
        tx_receipt = self.dbevmtx.get_receipt(cursor=cursor, tx_hash=tx_hash, chain_id=self.evm_inquirer.chain_id)  # noqa: E501
        if tx_receipt is not None:
            return tx_data, tx_receipt  # all good, tx receipt is in the database

        transaction, raw_receipt_data = self.evm_inquirer.get_transaction_by_hash(tx_hash)
        with self.database.conn.write_ctx() as write_cursor:
            self.dbevmtx.add_evm_transactions(
                write_cursor=write_cursor,
                evm_transactions=[transaction],
                relevant_address=relevant_address,
            )
            self.dbevmtx.add_or_ignore_receipt_data(
                write_cursor=write_cursor,
                chain_id=self.evm_inquirer.chain_id,
                data=raw_receipt_data,
            )

        tx_data = cursor.execute(query, bindings).fetchone()
        tx_receipt = self.dbevmtx.get_receipt(cursor, tx_hash, self.evm_inquirer.chain_id)
        return tx_data, tx_receipt  # type: ignore  # tx_data can't be None here

    def get_or_create_transaction(
            self,
            cursor: 'DBCursor',
            tx_hash: EVMTxHash,
            relevant_address: Optional['ChecksumEvmAddress'],
    ) -> tuple['EvmTransaction', 'EvmTxReceipt']:
        """Gets an evm transaction and its receipt from the database or
        if it doesn't exist, it pulls it from the data source and stores it in the database.
        It ensures that the requirements of
        the corresponding chain transaction are met before returning it. For example an
        evm transaction must have a corresponding receipt entry in the database.

        This function can raise:
        - pysqlcipher3.dbapi2.OperationalError if the SQL query fails due to invalid
        filtering arguments.
        - RemoteError if there is a problem querying the data source.
        - DeserializationError if the transaction cannot be deserialized from the DB.
        """
        if tx_hash == GENESIS_HASH:
            evm_tx, evm_tx_receipt = self.ensure_genesis_tx_data_exists()
        else:
            tx_data, evm_tx_receipt = self.ensure_tx_data_exists(
                cursor=cursor,
                tx_hash=tx_hash,
                relevant_address=relevant_address,
            )
            evm_tx = self.dbevmtx._build_evm_transaction(tx_data)

        return evm_tx, evm_tx_receipt

    def ensure_genesis_tx_data_exists(self) -> tuple['EvmTransaction', 'EvmTxReceipt']:
        """
        For each tracked account, query to see if it had any transactions in the genesis
        block. We check this even if there already is a 0x0..0 transaction in the db
        in order to be sure that genesis transactions are queried for all accounts.

        Returns the genesis transaction and its receipt
        """
        with self.database.conn.read_ctx() as cursor:
            accounts_data = self.database.get_blockchain_account_data(
                cursor=cursor,
                blockchain=self.evm_inquirer.chain_id.to_blockchain(),
            )
            for data in accounts_data:
                self._get_transactions_for_range(
                    address=data.address,
                    start_ts=Timestamp(0),
                    end_ts=Timestamp(0),
                )

        # Check whether the genesis tx was added
        with self.database.conn.read_ctx() as cursor:
            added_tx = self.dbevmtx.get_evm_transactions(
                cursor=cursor,
                filter_=EvmTransactionsFilterQuery.make(tx_hash=GENESIS_HASH, chain_id=self.evm_inquirer.chain_id),  # noqa: E501
                has_premium=True,  # we don't need any limiting here
            )

        if len(added_tx) == 0:
            raise InputError(
                f'There is no tracked {self.evm_inquirer.chain_id!s} address that '
                f'would have a genesis transaction',
            )

        tx_receipt_raw_data = self.evm_inquirer.get_transaction_receipt(tx_hash=GENESIS_HASH)
        with self.database.user_write() as write_cursor:
            self.dbevmtx.add_or_ignore_receipt_data(
                write_cursor=write_cursor,
                chain_id=self.evm_inquirer.chain_id,
                data=tx_receipt_raw_data,
            )

        with self.database.conn.read_ctx() as cursor:
            tx_receipt = self.dbevmtx.get_receipt(
                cursor=cursor,
                tx_hash=GENESIS_HASH,
                chain_id=self.evm_inquirer.chain_id,
            )

        return added_tx[0], tx_receipt  # type: ignore  # tx_receipt was just added in the DB so should be there

    def get_or_query_transaction_receipt(self, tx_hash: EVMTxHash) -> 'EvmTxReceipt':
        """
        Gets the receipt from the DB if it exists. If not queries the chain for it,
        saves it in the DB and then returns it.

        Also, if the actual transaction does not exist in the DB it queries it and saves it there.

        May raise:

        - DeserializationError
        - RemoteError if the transaction hash can't be found in any of the connected nodes
        """
        if tx_hash == GENESIS_HASH:
            _, tx_receipt = self.ensure_genesis_tx_data_exists()
        else:
            with self.database.conn.read_ctx() as cursor:
                # If the transaction is not in the DB then query it and add it
                transaction, tx_receipt = self.get_or_create_transaction(cursor=cursor, tx_hash=tx_hash, relevant_address=None)  # noqa: E501

            if transaction.to_address is not None:  # internal transactions only through contracts  # noqa: E501
                self._query_and_save_internal_transactions_for_range_or_parent_hash(
                    address=None,  # get all internal transactions for the parent hash
                    period_or_hash=tx_hash,
                )
        return tx_receipt

    def get_receipts_for_transactions_missing_them(
            self,
            limit: int | None = None,
            addresses: list[ChecksumEvmAddress] | None = None,
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
            if addresses is None:
                tx_filter_query = EvmTransactionsFilterQuery.make(
                    chain_id=self.evm_inquirer.chain_id,
                )
            else:
                tx_filter_query = EvmTransactionsFilterQuery.make(
                    accounts=[EvmAccount(address=x) for x in addresses],
                    chain_id=self.evm_inquirer.chain_id,
                )

            hash_results = self.dbevmtx.get_transaction_hashes_no_receipt(
                tx_filter_query=tx_filter_query,
                limit=limit,
            )

            if len(hash_results) == 0:
                return  # nothing to do

            for entry in hash_results:
                try:
                    tx_receipt_data = self.evm_inquirer.get_transaction_receipt(tx_hash=entry)
                except RemoteError as e:
                    self.msg_aggregator.add_warning(f'Failed to query information for {self.evm_inquirer.chain_name} transaction {entry.hex()} due to {e!s}. Skipping...')  # noqa: E501
                    continue

                with self.database.user_write() as write_cursor:
                    self.dbevmtx.add_or_ignore_receipt_data(
                        write_cursor=write_cursor,
                        chain_id=self.evm_inquirer.chain_id,
                        data=tx_receipt_data,
                    )

    def add_transaction_by_hash(
            self,
            tx_hash: EVMTxHash,
            associated_address: ChecksumEvmAddress,
            must_exist: bool = False,
    ) -> tuple['EvmTransaction', 'EvmTxReceipt']:
        """Adds a transaction to the database by its hash and associates it with the provided address.

        May raise:
        - RemoteError if any of the remote queries fail.
        - KeyError if there's a missing key in the tx_receipt dict.
        - DeserializationError if there's an issue deserializing a value.
        - InputError if the tx_hash or its receipt is not found on the blockchain or the address is not tracked.
        - AlreadyExists if the tx_hash and receipt are present in the db.
        """  # noqa: E501
        with self.database.conn.read_ctx() as cursor:
            tracked_accounts = self.database.get_blockchain_accounts(cursor).get(self.evm_inquirer.blockchain)  # noqa: E501
            if associated_address not in tracked_accounts:
                raise InputError(f'Address {associated_address} to associate with tx {tx_hash.hex()} is not tracked')  # noqa: E501

            if len(self.dbevmtx.get_evm_transactions(
                cursor=cursor,
                filter_=EvmTransactionsFilterQuery.make(tx_hash=tx_hash, chain_id=self.evm_inquirer.chain_id),  # noqa: E501
                has_premium=True,
            )) == 1 and self.dbevmtx.get_receipt(cursor=cursor, tx_hash=tx_hash, chain_id=self.evm_inquirer.chain_id) is not None:  # noqa: E501
                raise AlreadyExists(f'Transaction {tx_hash.hex()} is already in the DB')

        tx_result = self.evm_inquirer.maybe_get_transaction_by_hash(tx_hash=tx_hash, must_exist=must_exist)  # noqa: E501
        if tx_result is None:
            raise InputError(f'Transaction data for {tx_hash.hex()} not found on chain.')
        transaction, receipt_data = tx_result
        with self.database.user_write() as write_cursor:
            self.dbevmtx.add_evm_transactions(
                write_cursor=write_cursor,
                evm_transactions=[transaction],
                relevant_address=associated_address,
            )
            self.dbevmtx.add_or_ignore_receipt_data(
                write_cursor=write_cursor,
                chain_id=self.evm_inquirer.chain_id,
                data=receipt_data,
            )

        with self.dbevmtx.db.conn.read_ctx() as cursor:
            tx_receipt = self.dbevmtx.get_receipt(
                cursor=cursor,
                tx_hash=tx_hash,
                chain_id=self.evm_inquirer.chain_id,
            )
        assert tx_receipt is not None, 'transaction receipt was added just above, so should exist'
        return transaction, tx_receipt

    def get_chain_specific_multiaddress_data(
            self,
            addresses: Sequence[ChecksumEvmAddress],  # pylint: disable=unused-argument
            from_ts: Timestamp,  # pylint: disable=unused-argument
            to_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> None:
        """Can be implemented by each chain subclass to add chain-specific data queries
        for all tracked addresses at once"""
        return None
