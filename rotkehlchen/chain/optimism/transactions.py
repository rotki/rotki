import logging
from typing import TYPE_CHECKING, Optional, Union

from rotkehlchen.api.websockets.typedefs import TransactionStatusStep, WSMessageType
from rotkehlchen.chain.evm.constants import GENESIS_HASH
from rotkehlchen.chain.evm.transactions import EvmTransactions
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.db.filtering import OptimismTransactionsFilterQuery
from rotkehlchen.db.optimismtx import DBOptimismTx
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash, Timestamp, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.structures import EvmTxReceipt
    from rotkehlchen.db.dbhandler import DBHandler
    from .node_inquirer import OptimismInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

class OptimismTransactions(EvmTransactions):

    def __init__(
            self,
            optimism_inquirer: 'OptimismInquirer',
            database: 'DBHandler',
    ) -> None:
        super().__init__(evm_inquirer=optimism_inquirer, database=database)

    def _query_and_save_transactions_for_range(
            self,
            address: ChecksumEvmAddress,
            period: TimestampOrBlockRange,
            location_string: Optional[str] = None,
    ) -> None:
        """Helper function to abstract tx querying functionality for different range types"""
        dbevmtx = DBOptimismTx(self.database)
        for new_transactions in self.evm_inquirer.etherscan.get_transactions(
                account=address,
                action='txlist',
                period_or_hash=period,
        ):
            # add new transactions to the DB
            if len(new_transactions) == 0:
                continue

            with self.database.user_write() as write_cursor:
                dbevmtx.add_optimism_transactions(
                    write_cursor=write_cursor,
                    optimism_transactions=new_transactions,
                    relevant_address=address,
                )
            if period.range_type == 'timestamps':
                assert location_string, 'should always be given for timestamps'
                with self.database.user_write() as write_cursor:
                    # update last queried time for the address
                    self.dbranges.update_used_query_range(
                        write_cursor=write_cursor,
                        location_string=location_string,
                        queried_ranges=[(period.from_value, new_transactions[-1].timestamp)],  # type: ignore  # noqa: E501
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
    
    def _query_and_save_internal_transactions_for_range_or_parent_hash(
            self,
            address: Optional[ChecksumEvmAddress],
            period_or_hash: Union[TimestampOrBlockRange, EVMTxHash],
            location_string: Optional[str] = None,
    ) -> None:
        """Helper function to abstract internal tx querying for different range types
        or for a specific parent transaction hash.

        If address is None, then etherscan query will return all internal transactions.
        """
        dbevmtx = DBOptimismTx(self.database)
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
                    result = dbevmtx.get_optimism_transactions(
                        cursor,
                        OptimismTransactionsFilterQuery.make(
                            tx_hash=internal_tx.parent_tx_hash,
                            chain_id=self.evm_inquirer.chain_id,
                        ),
                        has_premium=True,  # ignore limiting here
                    )
                if len(result) == 0:  # parent transaction is not in the DB. Get it
                    transaction, raw_receipt_data = self.evm_inquirer.get_transaction_by_hash(internal_tx.parent_tx_hash)  # noqa: E501
                    with self.database.conn.write_ctx() as write_cursor:
                        dbevmtx.add_optimism_transactions(
                            write_cursor=write_cursor,
                            optimism_transactions=[transaction],
                            relevant_address=address,
                        )
                        dbevmtx.add_receipt_data(
                            write_cursor=write_cursor,
                            chain_id=self.evm_inquirer.chain_id,
                            data=raw_receipt_data,
                        )
                    timestamp = transaction.timestamp
                else:
                    timestamp = result[0].timestamp

                with self.database.conn.write_ctx() as write_cursor:
                    dbevmtx.add_evm_internal_transactions(
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
                            queried_ranges=[(period_or_hash.from_value, timestamp)],  # type: ignore  # noqa: E501
                        )

                    self.msg_aggregator.add_message(
                        message_type=WSMessageType.EVM_TRANSACTION_STATUS,
                        data={
                            'address': address,
                            'evm_chain': self.evm_inquirer.chain_id.to_name(),
                            'period': [period_or_hash.from_value, timestamp],
                            'status': str(TransactionStatusStep.QUERYING_INTERNAL_TRANSACTIONS),  # noqa: E501
                        },
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
        dbevmtx = DBOptimismTx(self.database)
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
                        tx_hash_bytes = deserialize_evm_tx_hash(tx_hash)
                        with self.database.conn.read_ctx() as cursor:
                            result = dbevmtx.get_optimism_transactions(
                                cursor,
                                OptimismTransactionsFilterQuery.make(tx_hash=tx_hash_bytes, chain_id=self.evm_inquirer.chain_id),  # noqa: E501
                                has_premium=True,  # ignore limiting here
                            )
                        if len(result) == 0:  # if transaction is not there add it
                            transaction, raw_receipt_data = self.evm_inquirer.get_transaction_by_hash(tx_hash_bytes)  # noqa: E501
                            with self.database.user_write() as write_cursor:
                                dbevmtx.add_optimism_transactions(
                                    write_cursor=write_cursor,
                                    optimism_transactions=[transaction],
                                    relevant_address=address,
                                )
                                dbevmtx.add_receipt_data(
                                    write_cursor=write_cursor,
                                    chain_id=self.evm_inquirer.chain_id,
                                    data=raw_receipt_data,
                                )
                            timestamp = transaction.timestamp
                        else:
                            timestamp = result[0].timestamp

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
    
    def get_or_query_transaction_receipt(self, tx_hash: EVMTxHash) -> 'EvmTxReceipt':
        """
        Gets the receipt from the DB if it exists. If not queries the chain for it,
        saves it in the DB and then returns it.

        Also, if the actual transaction does not exist in the DB it queries it and saves it there.

        May raise:

        - DeserializationError
        - RemoteError if the transaction hash can't be found in any of the connected nodes
        """
        dbevmtx = DBOptimismTx(self.database)
        with self.database.conn.read_ctx() as cursor:
            # If the transaction is not in the DB then query it and add it
            result = dbevmtx.get_optimism_transactions(
                cursor=cursor,
                filter_=OptimismTransactionsFilterQuery.make(tx_hash=tx_hash, chain_id=self.evm_inquirer.chain_id),  # noqa: E501
                has_premium=True,  # we don't need any limiting here
            )

        if tx_hash == GENESIS_HASH:
            # For each tracked account, query to see if it had any transactions in the
            # genesis block. We check this even if there already is a 0x0..0 transaction in the db
            # in order to be sure that genesis transactions are queried for all accounts.
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
                added_tx = dbevmtx.get_optimism_transactions(
                    cursor=cursor,
                    filter_=OptimismTransactionsFilterQuery.make(tx_hash=GENESIS_HASH, chain_id=self.evm_inquirer.chain_id),  # noqa: E501
                    has_premium=True,  # we don't need any limiting here
                )

            if len(added_tx) == 0:
                raise InputError(
                    f'There is no tracked {self.evm_inquirer.chain_id!s} address that '
                    f'would have a genesis transaction',
                )
        elif len(result) == 0:  # normal functionality
            tx_result = self.evm_inquirer.maybe_get_transaction_by_hash(tx_hash)
            if tx_result is None:
                raise RemoteError(
                    f'Transaction with hash {tx_hash.hex()} for '
                    f'{self.evm_inquirer.chain_name} not found',
                )
            transaction, raw_receipt_data = tx_result
            with self.database.user_write() as write_cursor:
                dbevmtx.add_optimism_transactions(write_cursor, [transaction], relevant_address=None)  # noqa: E501
                dbevmtx.add_receipt_data(
                    write_cursor=write_cursor,
                    chain_id=self.evm_inquirer.chain_id,
                    data=raw_receipt_data,
                )
            if transaction.to_address is not None:  # internal transactions only through contracts  # noqa: E501
                self._query_and_save_internal_transactions_for_range_or_parent_hash(
                    address=None,  # get all internal transactions for the parent hash
                    period_or_hash=tx_hash,
                )

        with self.database.conn.read_ctx() as cursor:
            tx_receipt = dbevmtx.get_receipt(
                cursor=cursor,
                tx_hash=tx_hash,
                chain_id=self.evm_inquirer.chain_id,
            )
        if tx_receipt is not None:
            return tx_receipt

        # not in the DB, so we need to query the chain for it
        tx_receipt_raw_data = self.evm_inquirer.get_transaction_receipt(tx_hash=tx_hash)
        try:
            with self.database.user_write() as write_cursor:
                dbevmtx.add_receipt_data(
                    write_cursor=write_cursor,
                    chain_id=self.evm_inquirer.chain_id,
                    data=tx_receipt_raw_data,
                )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            if 'UNIQUE constraint failed: evmtx_receipts.tx_hash' not in str(e):
                raise  # otherwise something else added the receipt before so we just continue
        with self.database.conn.read_ctx() as cursor:
            tx_receipt = dbevmtx.get_receipt(
                cursor=cursor,
                tx_hash=tx_hash,
                chain_id=self.evm_inquirer.chain_id,
            )

        return tx_receipt  # type: ignore  # tx_receipt was just added in the DB so should be there  # noqa: E501
    
    def add_transaction_by_hash(
            self,
            tx_hash: EVMTxHash,
            associated_address: ChecksumEvmAddress,
    ) -> tuple['OptimismTransaction', 'EvmTxReceipt']:
        """Adds a transaction to the database by its hash and associates it with the provided address.

        May raise:
        - RemoteError if any of the remote queries fail.
        - KeyError if there's a missing key in the tx_receipt dict.
        - DeserializationError if there's an issue deserializing a value.
        - InputError if the tx_hash or its receipt is not found on the blockchain.
        - pysqlcipher3.dbapi2.IntegrityError if the tx_hash is present in the db or address is not tracked.
        """  # noqa: E501
        dbevmtx = DBOptimismTx(self.database)
        tx_result = self.evm_inquirer.maybe_get_transaction_by_hash(tx_hash)
        if tx_result is None:
            raise InputError(f'Transaction data for {tx_hash.hex()} not found on chain.')
        transaction, receipt_data = tx_result
        with self.database.user_write() as write_cursor:
            dbevmtx.add_optimism_transactions(
                write_cursor=write_cursor,
                optimism_transactions=[transaction],
                relevant_address=associated_address,
            )
            dbevmtx.add_receipt_data(
                write_cursor=write_cursor,
                chain_id=self.evm_inquirer.chain_id,
                data=receipt_data,
            )
        with dbevmtx.db.conn.read_ctx() as cursor:
            tx_receipt = dbevmtx.get_receipt(
                cursor=cursor,
                tx_hash=tx_hash,
                chain_id=self.evm_inquirer.chain_id,
            )
        assert tx_receipt is not None, 'transaction receipt was added just above, so should exist'  # noqa: E501
        return transaction, tx_receipt

