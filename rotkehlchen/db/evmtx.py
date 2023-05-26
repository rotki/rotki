import logging
from typing import TYPE_CHECKING, Any, Optional, get_args

from rotkehlchen.chain.ethereum.constants import ETHEREUM_GENESIS
from rotkehlchen.chain.evm.constants import GENESIS_HASH, ZERO_ADDRESS
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import EvmAccount
from rotkehlchen.chain.optimism.constants import OPTIMISM_GENESIS
from rotkehlchen.chain.polygon_pos.constants import POLYGON_POS_GENESIS
from rotkehlchen.db.constants import HISTORY_MAPPING_STATE_DECODED
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery, TransactionsNotDecodedFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address, deserialize_timestamp
from rotkehlchen.types import (
    SUPPORTED_CHAIN_IDS,
    SUPPORTED_EVM_CHAINS,
    ChainID,
    ChecksumEvmAddress,
    EvmInternalTransaction,
    EvmTransaction,
    EVMTxHash,
    SupportedBlockchain,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes
from rotkehlchen.utils.misc import hexstr_to_int

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

from rotkehlchen.constants.limits import FREE_ETH_TX_LIMIT

TRANSACTIONS_MISSING_DECODING_QUERY = (
    'evmtx_receipts AS A LEFT OUTER JOIN evm_tx_mappings AS B ON A.tx_hash=B.tx_hash '
    'AND A.chain_id=B.chain_ID LEFT JOIN evm_transactions AS C on '
    'A.tx_hash=C.tx_hash '
)


class DBEvmTx():

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    def add_evm_transactions(
            self,
            write_cursor: 'DBCursor',
            evm_transactions: list[EvmTransaction],
            relevant_address: Optional[ChecksumEvmAddress],
    ) -> None:
        """Adds evm transactions to the database"""
        tx_tuples: list[tuple[Any, ...]] = []
        for tx in evm_transactions:
            tx_tuples.append((
                tx.tx_hash,
                tx.chain_id.serialize_for_db(),
                tx.timestamp,
                tx.block_number,
                tx.from_address,
                tx.to_address,
                str(tx.value),
                str(tx.gas),
                str(tx.gas_price),
                str(tx.gas_used),
                tx.input_data,
                tx.nonce,
            ))

        query = """
            INSERT INTO evm_transactions(
              tx_hash,
              chain_id,
              timestamp,
              block_number,
              from_address,
              to_address,
              value,
              gas,
              gas_price,
              gas_used,
              input_data,
              nonce)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.db.write_tuples(
            write_cursor=write_cursor,
            tuple_type='evm_transaction',
            query=query,
            tuples=tx_tuples,
            relevant_address=relevant_address,
        )

    def add_evm_internal_transactions(
            self,
            write_cursor: 'DBCursor',
            transactions: list[EvmInternalTransaction],
            relevant_address: Optional[ChecksumEvmAddress],
    ) -> None:
        """Adds evm internal transactions to the database"""
        tx_tuples: list[tuple[Any, ...]] = []
        for tx in transactions:
            tx_tuples.append((
                tx.parent_tx_hash,
                tx.chain_id.serialize_for_db(),
                tx.trace_id,
                tx.from_address,
                tx.to_address,
                str(tx.value),
            ))

        query = """
            INSERT INTO evm_internal_transactions(
              parent_tx_hash,
              chain_id,
              trace_id,
              from_address,
              to_address,
              value)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        self.db.write_tuples(
            write_cursor=write_cursor,
            tuple_type='evm_transaction',
            query=query,
            tuples=tx_tuples,
            relevant_address=relevant_address,
        )

    def get_evm_internal_transactions(
            self,
            parent_tx_hash: EVMTxHash,
            blockchain: SupportedBlockchain,
    ) -> list[EvmInternalTransaction]:
        """Get all internal transactions under a parent tx_hash for a given chain"""
        chain_id = blockchain.to_chain_id().serialize_for_db()
        cursor = self.db.conn.cursor()
        results = cursor.execute(
            'SELECT parent_tx_hash, chain_id, trace_id, from_address, to_address, value '
            'FROM evm_internal_transactions WHERE parent_tx_hash=? AND chain_id=?',
            (parent_tx_hash, chain_id),
        )
        transactions = []
        for result in results:
            tx = EvmInternalTransaction(
                parent_tx_hash=deserialize_evm_tx_hash(result[0]),
                chain_id=ChainID.deserialize_from_db(result[1]),
                trace_id=result[2],
                from_address=result[3],
                to_address=result[4],
                value=result[5],
            )
            transactions.append(tx)

        return transactions

    def get_evm_transactions(
            self,
            cursor: 'DBCursor',
            filter_: EvmTransactionsFilterQuery,
            has_premium: bool,
    ) -> list[EvmTransaction]:
        """Returns a list of evm transactions optionally filtered by
        the given filter query

        This function can raise:
        - pysqlcipher3.dbapi2.OperationalError if the SQL query fails due to invalid
        filtering arguments.
        """
        query, bindings = filter_.prepare()
        if has_premium:
            query = 'SELECT DISTINCT evm_transactions.tx_hash, evm_transactions.chain_id, timestamp, block_number, from_address, to_address, value, gas, gas_price, gas_used, input_data, nonce FROM evm_transactions ' + query  # noqa: E501
            results = cursor.execute(query, bindings)
        else:
            query = 'SELECT DISTINCT evm_transactions.tx_hash, evm_transactions.chain_id, timestamp, block_number, from_address, to_address, value, gas, gas_price, gas_used, input_data, nonce FROM (SELECT * from evm_transactions ORDER BY timestamp DESC LIMIT ?) evm_transactions ' + query  # noqa: E501
            results = cursor.execute(query, [FREE_ETH_TX_LIMIT] + bindings)

        evm_transactions = []
        for result in results:
            try:
                tx = EvmTransaction(
                    tx_hash=deserialize_evm_tx_hash(result[0]),
                    chain_id=ChainID.deserialize_from_db(result[1]),
                    timestamp=deserialize_timestamp(result[2]),
                    block_number=result[3],
                    from_address=result[4],
                    to_address=result[5],
                    value=int(result[6]),
                    gas=int(result[7]),
                    gas_price=int(result[8]),
                    gas_used=int(result[9]),
                    input_data=result[10],
                    nonce=result[11],
                )
            except DeserializationError as e:
                self.db.msg_aggregator.add_error(
                    f'Error deserializing evm transaction from the DB. '
                    f'Skipping it. Error was: {e!s}',
                )
                continue

            evm_transactions.append(tx)

        return evm_transactions

    def get_evm_transactions_and_limit_info(
            self,
            cursor: 'DBCursor',
            filter_: EvmTransactionsFilterQuery,
            has_premium: bool,
    ) -> tuple[list[EvmTransaction], int]:
        """Gets all evm transactions for the query from the DB.

        Also returns how many are the total found for the filter.
        """
        txs = self.get_evm_transactions(cursor, filter_=filter_, has_premium=has_premium)
        query, bindings = filter_.prepare(with_pagination=False)
        query = 'SELECT COUNT(DISTINCT evm_transactions.tx_hash) FROM evm_transactions ' + query  # noqa: E501
        total_found_result = cursor.execute(query, bindings)
        return txs, total_found_result.fetchone()[0]  # always returns result

    def purge_evm_transaction_data(self, chain: Optional[SUPPORTED_EVM_CHAINS]) -> None:
        """Deletes all evm transaction related data from the DB"""
        query_ranges_tuples = []
        delete_query = 'DELETE FROM evm_transactions'
        delete_bindings = ()
        if chain is not None:
            chains = [chain]
            delete_query += ' WHERE chain_id = ?'
            delete_bindings = (chain.to_chain_id().serialize_for_db(),)    # type: ignore[assignment]  # noqa: E501
        else:
            chains = get_args(SUPPORTED_EVM_CHAINS)  # type: ignore[assignment]

        for entry in chains:
            query_ranges_tuples.extend([
                (f'{entry.to_range_prefix("txs")}\\_%', '\\'),
                (f'{entry.to_range_prefix("internaltxs")}\\_%', '\\'),
                (f'{entry.to_range_prefix("tokentxs")}\\_%', '\\'),
            ])
        with self.db.user_write() as cursor:
            cursor.executemany(
                'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
                query_ranges_tuples,
            )
            cursor.execute(delete_query, delete_bindings)

    def get_transaction_hashes_no_receipt(
            self,
            tx_filter_query: Optional[EvmTransactionsFilterQuery],
            limit: Optional[int],
    ) -> list[EVMTxHash]:
        cursor = self.db.conn.cursor()
        querystr = 'SELECT DISTINCT evm_transactions.tx_hash FROM evm_transactions '
        bindings = ()
        if tx_filter_query is not None:
            filter_query, bindings = tx_filter_query.prepare(with_order=False, with_pagination=False)  # type: ignore  # noqa: E501
            querystr += filter_query + ' AND '
        else:
            querystr += ' WHERE '

        querystr += 'evm_transactions.tx_hash NOT IN (SELECT tx_hash from evmtx_receipts)'
        if limit is not None:
            querystr += 'LIMIT ?'
            bindings = (*bindings, limit)  # type: ignore

        cursor_result = cursor.execute(querystr, bindings)
        hashes = []
        for entry in cursor_result:
            try:
                hashes.append(deserialize_evm_tx_hash(entry[0]))
            except DeserializationError as e:
                log.debug(f'Got error {e!s} while deserializing tx_hash {entry[0]} from the DB')

        return hashes

    def get_transaction_hashes_not_decoded(
            self,
            chain_id: Optional[ChainID],
            limit: Optional[int],
            addresses: Optional[list[ChecksumEvmAddress]],
    ) -> list[EVMTxHash]:
        """Get transaction hashes for the transactions that have not been decoded.
        Optionally by chain id.
        If the limit argument is provided then it is used in the SQL query with
        the default order.
        When the addresses argument is provided only the transactions involving those
        addresses are decoded.
        """
        query, bindings = TransactionsNotDecodedFilterQuery.make(
            limit=limit,
            addresses=addresses,
            chain_id=chain_id,
        ).prepare()
        querystr = 'SELECT A.tx_hash from ' + TRANSACTIONS_MISSING_DECODING_QUERY + query

        with self.db.conn.read_ctx() as cursor:
            cursor.execute(querystr, bindings)
            return [deserialize_evm_tx_hash(x[0]) for x in cursor]

    def count_hashes_not_decoded(
            self,
            chain_id: Optional[ChainID],
            addresses: Optional[list[ChecksumEvmAddress]],
    ) -> int:
        """
        Count the number of transactions queried that have not been decoded. When the addresses
        argument is provided only the transactions involving those addresses are decoded.
        """
        query, bindings = TransactionsNotDecodedFilterQuery.make(
            limit=None,
            addresses=addresses,
            chain_id=chain_id,
        ).prepare()

        querystr = 'SELECT COUNT(*) FROM ' + TRANSACTIONS_MISSING_DECODING_QUERY + query
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(querystr, bindings)
            return cursor.fetchone()[0]

    def add_receipt_data(
            self,
            write_cursor: 'DBCursor',
            chain_id: ChainID,
            data: dict[str, Any],
    ) -> None:
        """Add tx receipt data as they are returned by the chain to the DB

        Also need to provide the chain id.

        This assumes the transaction is already in the DB.

        May raise:
        - Key Error if any of the expected fields are missing
        - DeserializationError if there is a problem deserializing a value
        - pysqlcipher3.dbapi2.IntegrityError if the transaction hash is not in the DB:
        pysqlcipher3.dbapi2.IntegrityError: FOREIGN KEY constraint failed
        If the receipt already exists in the DB:
        pysqlcipher3.dbapi2.IntegrityError: UNIQUE constraint failed: evmtx_receipts.tx_hash
        """
        tx_hash_b = hexstring_to_bytes(data['transactionHash'])
        # some nodes miss the type field for older non EIP1559 transactions. So assume legacy (0)
        tx_type = hexstr_to_int(data.get('type', '0x0'))
        status = data.get('status', 1)  # status may be missing for older txs. Assume 1.
        serialized_chain_id = chain_id.serialize_for_db()
        if status is None:
            status = 1
        contract_address = deserialize_evm_address(data['contractAddress']) if data['contractAddress'] else None  # noqa: E501
        write_cursor.execute(
            'INSERT INTO evmtx_receipts (tx_hash, chain_id, contract_address, status, type) '
            'VALUES(?, ?, ?, ?, ?) ',
            (tx_hash_b, serialized_chain_id, contract_address, status, tx_type),
        )

        log_tuples = []
        topic_tuples = []
        for log_entry in data['logs']:
            log_index = log_entry['logIndex']
            log_tuples.append((
                tx_hash_b,
                serialized_chain_id,
                log_index,
                hexstring_to_bytes(log_entry['data']),
                deserialize_evm_address(log_entry['address']),
                int(log_entry['removed']),
            ))

            for idx, topic in enumerate(log_entry['topics']):
                topic_tuples.append((
                    tx_hash_b,
                    serialized_chain_id,
                    log_index,
                    hexstring_to_bytes(topic),
                    idx,
                ))

        if len(log_tuples) != 0:
            write_cursor.executemany(
                'INSERT INTO evmtx_receipt_logs (tx_hash, chain_id, log_index, data, address, removed) '  # noqa: E501
                'VALUES(? ,? ,? ,? ,?, ?)',
                log_tuples,
            )

            if len(topic_tuples) != 0:
                write_cursor.executemany(
                    'INSERT INTO evmtx_receipt_log_topics (tx_hash, chain_id, log_index, topic, topic_index) '  # noqa: E501
                    'VALUES(? ,? ,?, ?, ?)',
                    topic_tuples,
                )

    def get_receipt(
            self,
            cursor: 'DBCursor',
            tx_hash: EVMTxHash,
            chain_id: ChainID,
    ) -> Optional[EvmTxReceipt]:
        """Get the evm receipt for the given tx_hash and chain id"""
        chain_id_serialized = chain_id.serialize_for_db()
        cursor.execute(
            'SELECT contract_address, status, type from evmtx_receipts WHERE tx_hash=? AND chain_id=?',  # noqa: E501
            (tx_hash, chain_id_serialized))
        result = cursor.fetchone()
        if result is None:
            return None

        tx_receipt = EvmTxReceipt(
            tx_hash=tx_hash,
            chain_id=chain_id,
            contract_address=result[0],
            status=bool(result[1]),  # works since value is either 0 or 1
            type=result[2],
        )

        cursor.execute(
            'SELECT log_index, data, address, removed from evmtx_receipt_logs WHERE tx_hash=? AND chain_id=?',  # noqa: E501
            (tx_hash, chain_id_serialized))
        with self.db.conn.read_ctx() as other_cursor:
            for result in cursor:
                log_index = result[0]
                tx_receipt_log = EvmTxReceiptLog(
                    log_index=log_index,
                    data=result[1],
                    address=result[2],
                    removed=bool(result[3]),  # works since value is either 0 or 1
                )
                other_cursor.execute(
                    'SELECT topic from evmtx_receipt_log_topics '
                    'WHERE tx_hash=? AND log_index=? AND chain_id=?'
                    'ORDER BY topic_index ASC',
                    (tx_hash, log_index, chain_id_serialized),
                )
                for topic_result in other_cursor:
                    tx_receipt_log.topics.append(topic_result[0])

                tx_receipt.logs.append(tx_receipt_log)

        return tx_receipt

    def delete_transactions(
            self,
            write_cursor: 'DBCursor',
            address: ChecksumEvmAddress,
            chain: SUPPORTED_EVM_CHAINS,
    ) -> None:
        """Delete all of the particular evm chain transactions related data
        to the given address from the DB.

        So transactions, receipts, logs and decoded events, except for those
        whose events are customized.
        """
        dbevents = DBHistoryEvents(self.db)
        chain_id = chain.to_chain_id()
        chain_id_serialized = chain_id.serialize_for_db()
        write_cursor.executemany(
            'DELETE FROM used_query_ranges WHERE name=?;',
            [
                (f'{chain.to_range_prefix("txs")}_{address}',),
                (f'{chain.to_range_prefix("internaltxs")}_{address}',),
                (f'{chain.to_range_prefix("tokentxs")}_{address}',),
            ],
        )
        # Get all tx_hashes that are touched by this address and no other address for the chain
        result = write_cursor.execute(
            'SELECT tx_hash from evmtx_address_mappings WHERE address=? AND chain_id=? AND tx_hash NOT IN ( '  # noqa: E501
            'SELECT tx_hash from evmtx_address_mappings WHERE address!=? AND chain_id=?'
            ')',
            (address, chain_id_serialized, address, chain_id_serialized),
        )
        tx_hashes = [deserialize_evm_tx_hash(x[0]) for x in result]
        if len(tx_hashes) == 0:
            # Need to handle the genesis tx separately since our single genesis tx contains
            # multiple genesis transactions from multiple addresses.
            genesis_tx_exists = write_cursor.execute(
                'SELECT COUNT(tx_hash) FROM evmtx_address_mappings WHERE tx_hash = ?',
                (GENESIS_HASH,),
            ).fetchone()[0] != 0
            if genesis_tx_exists is False:
                return

        dbevents.delete_events_by_tx_hash(
            write_cursor=write_cursor,
            tx_hashes=tx_hashes,
            chain_id=chain_id,  # type: ignore[arg-type] # comes from SUPPORTED_EVM_CHAINS
        )
        write_cursor.execute(  # delete genesis tx events related to the provided address
            'DELETE FROM history_events WHERE identifier IN ('
            'SELECT H.identifier from history_events H INNER JOIN evm_events_info E '
            'ON H.identifier=E.identifier WHERE E.tx_hash=? AND H.location_label=?)',
            (GENESIS_HASH, address),
        )
        genesis_events_count = write_cursor.execute(
            'SELECT COUNT (*) FROM history_events H INNER JOIN evm_events_info E'
            ' WHERE H.identifier=E.identifier and E.tx_hash=?',
            (GENESIS_HASH,),
        ).fetchone()[0]
        if genesis_events_count == 0:
            # If there are no more events in the genesis tx, delete it
            tx_hashes.append(GENESIS_HASH)

        # Now delete all relevant transactions. By deleting all relevant transactions all tables
        # are cleared thanks to cascading (except for history_events which was cleared above)
        write_cursor.executemany(
            'DELETE FROM evm_transactions WHERE tx_hash=? AND chain_id=? AND tx_hash NOT IN (SELECT tx_hash FROM evm_events_info)',  # noqa: E501
            [(x, chain_id_serialized) for x in tx_hashes],
        )
        # Delete all remaining evm_tx_mappings so decoding can happen again for customized events
        write_cursor.executemany(
            'DELETE FROM evm_tx_mappings WHERE tx_hash=? AND chain_id=? AND value=?',
            [(x, chain_id_serialized, HISTORY_MAPPING_STATE_DECODED) for x in tx_hashes],
        )

    def get_queried_range(
            self,
            cursor: 'DBCursor',
            address: ChecksumEvmAddress,
            chain: SUPPORTED_EVM_CHAINS,
    ) -> tuple[Timestamp, Timestamp]:
        """Gets the most conservative range that was queried for the
        transactions of an address for a specific evm chain

        That means the least common denominator of normal, internal and token transactions
        """
        starts = []
        ends = []
        prefixes = [chain.to_range_prefix('txs'), chain.to_range_prefix('internaltxs'), chain.to_range_prefix('tokentxs')]  # noqa: E501
        for prefix in prefixes:
            tx_range = self.db.get_used_query_range(cursor, f'{prefix}_{address}')
            if tx_range is None:  # if any range is missing then we gotta requery
                return Timestamp(0), Timestamp(0)

            starts.append(tx_range[0])
            ends.append(tx_range[1])

        return max(starts), min(ends)

    def get_max_genesis_trace_id(self, chain_id: ChainID) -> int:
        """Get the max trace id of genesis internal transactions from the database.
        If no internal transactions were found, returns 0 (zero)."""
        cursor = self.db.conn.cursor()
        trace_id, = cursor.execute(
            'SELECT MAX(trace_id) from evm_internal_transactions '
            'WHERE parent_tx_hash=? and chain_id=?',
            (GENESIS_HASH, chain_id.serialize_for_db()),
        ).fetchone()
        return trace_id if trace_id is not None else 0

    def get_or_create_genesis_transaction(
            self,
            account: ChecksumEvmAddress,
            chain_id: SUPPORTED_CHAIN_IDS,
    ) -> EvmTransaction:
        with self.db.conn.read_ctx() as cursor:
            tx_in_db = self.get_evm_transactions(
                cursor=cursor,
                filter_=EvmTransactionsFilterQuery.make(
                    tx_hash=GENESIS_HASH,
                    accounts=[EvmAccount(address=account)],
                    chain_id=chain_id,
                ),
                has_premium=True,
            )
        if len(tx_in_db) == 1:
            tx = tx_in_db[0]
        else:
            if chain_id == ChainID.ETHEREUM:
                timestamp = ETHEREUM_GENESIS
            elif chain_id == ChainID.OPTIMISM:
                timestamp = OPTIMISM_GENESIS
            else:
                timestamp = POLYGON_POS_GENESIS
            tx = EvmTransaction(
                chain_id=chain_id,
                timestamp=timestamp,
                block_number=0,
                tx_hash=GENESIS_HASH,
                from_address=ZERO_ADDRESS,
                to_address=None,
                value=0,
                gas=0,
                gas_price=0,
                gas_used=0,
                input_data=b'',
                nonce=0,
            )
            with self.db.user_write() as cursor:
                self.add_evm_transactions(
                    write_cursor=cursor,
                    evm_transactions=[tx],
                    relevant_address=account,
                )
        return tx
