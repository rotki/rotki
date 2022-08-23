import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from rotkehlchen.chain.ethereum.constants import (
    ETHEREUM_BEGIN,
    GENESIS_HASH,
    RANGE_PREFIX_ETHINTERNALTX,
    RANGE_PREFIX_ETHTOKENTX,
    RANGE_PREFIX_ETHTX,
    ZERO_ADDRESS,
)
from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt, EthereumTxReceiptLog
from rotkehlchen.db.constants import HISTORY_MAPPING_DECODED
from rotkehlchen.db.filtering import ETHTransactionsFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_ethereum_address,
    deserialize_timestamp,
)
from rotkehlchen.types import (
    ChecksumEvmAddress,
    EthereumInternalTransaction,
    EthereumTransaction,
    EVMTxHash,
    Timestamp,
    deserialize_evm_tx_hash,
    make_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes
from rotkehlchen.utils.misc import hexstr_to_int

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

from rotkehlchen.constants.limits import FREE_ETH_TX_LIMIT


class DBEthTx():

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    def add_ethereum_transactions(
            self,
            write_cursor: 'DBCursor',
            ethereum_transactions: List[EthereumTransaction],
            relevant_address: Optional[ChecksumEvmAddress],
    ) -> None:
        """Adds ethereum transactions to the database"""
        tx_tuples: List[Tuple[Any, ...]] = []
        for tx in ethereum_transactions:
            tx_tuples.append((
                tx.tx_hash,
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
            INSERT INTO ethereum_transactions(
              tx_hash,
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.db.write_tuples(
            write_cursor=write_cursor,
            tuple_type='ethereum_transaction',
            query=query,
            tuples=tx_tuples,
            relevant_address=relevant_address,
        )

    def add_ethereum_internal_transactions(
            self,
            write_cursor: 'DBCursor',
            transactions: List[EthereumInternalTransaction],
            relevant_address: ChecksumEvmAddress,
    ) -> None:
        """Adds ethereum transactions to the database"""
        tx_tuples: List[Tuple[Any, ...]] = []
        for tx in transactions:
            tx_tuples.append((
                tx.parent_tx_hash,
                tx.trace_id,
                tx.timestamp,
                tx.block_number,
                tx.from_address,
                tx.to_address,
                str(tx.value),
            ))

        query = """
            INSERT INTO ethereum_internal_transactions(
              parent_tx_hash,
              trace_id,
              timestamp,
              block_number,
              from_address,
              to_address,
              value)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self.db.write_tuples(
            write_cursor=write_cursor,
            tuple_type='ethereum_transaction',
            query=query,
            tuples=tx_tuples,
            relevant_address=relevant_address,
        )

    def get_ethereum_internal_transactions(
            self,
            parent_tx_hash: EVMTxHash,
    ) -> List[EthereumInternalTransaction]:
        """Get all internal transactions under a parent tx_hash"""
        cursor = self.db.conn.cursor()
        results = cursor.execute(
            'SELECT * from ethereum_internal_transactions WHERE parent_tx_hash=?',
            (parent_tx_hash,),
        )
        transactions = []
        for result in results:
            tx = EthereumInternalTransaction(
                parent_tx_hash=make_evm_tx_hash(result[0]),
                trace_id=result[1],
                timestamp=result[2],
                block_number=result[3],
                from_address=result[4],
                to_address=result[5],
                value=result[6],
            )
            transactions.append(tx)

        return transactions

    def get_ethereum_transactions(
            self,
            cursor: 'DBCursor',
            filter_: ETHTransactionsFilterQuery,
            has_premium: bool,
    ) -> List[EthereumTransaction]:
        """Returns a list of ethereum transactions optionally filtered by
        the given filter query

        This function can raise:
        - pysqlcipher3.dbapi2.OperationalError if the SQL query fails due to invalid
        filtering arguments.
        """
        query, bindings = filter_.prepare()
        if has_premium:
            query = 'SELECT DISTINCT ethereum_transactions.tx_hash, timestamp, block_number, from_address, to_address, value, gas, gas_price, gas_used, input_data, nonce FROM ethereum_transactions ' + query  # noqa: E501
            results = cursor.execute(query, bindings)
        else:
            query = 'SELECT DISTINCT ethereum_transactions.tx_hash, timestamp, block_number, from_address, to_address, value, gas, gas_price, gas_used, input_data, nonce FROM (SELECT * from ethereum_transactions ORDER BY timestamp DESC LIMIT ?) ethereum_transactions ' + query  # noqa: E501
            results = cursor.execute(query, [FREE_ETH_TX_LIMIT] + bindings)

        ethereum_transactions = []
        for result in results:
            try:
                tx = EthereumTransaction(
                    tx_hash=make_evm_tx_hash(result[0]),
                    timestamp=deserialize_timestamp(result[1]),
                    block_number=result[2],
                    from_address=result[3],
                    to_address=result[4],
                    value=int(result[5]),
                    gas=int(result[6]),
                    gas_price=int(result[7]),
                    gas_used=int(result[8]),
                    input_data=result[9],
                    nonce=result[10],
                )
            except DeserializationError as e:
                self.db.msg_aggregator.add_error(
                    f'Error deserializing ethereum transaction from the DB. '
                    f'Skipping it. Error was: {str(e)}',
                )
                continue

            ethereum_transactions.append(tx)

        return ethereum_transactions

    def get_ethereum_transactions_and_limit_info(
            self,
            cursor: 'DBCursor',
            filter_: ETHTransactionsFilterQuery,
            has_premium: bool,
    ) -> Tuple[List[EthereumTransaction], int]:
        """Gets all ethereum transactions for the query from the D.

        Also returns how many are the total found for the filter.
        """
        txs = self.get_ethereum_transactions(cursor, filter_=filter_, has_premium=has_premium)
        query, bindings = filter_.prepare(with_pagination=False)
        query = 'SELECT COUNT(DISTINCT ethereum_transactions.tx_hash) FROM ethereum_transactions ' + query  # noqa: E501
        total_found_result = cursor.execute(query, bindings)
        return txs, total_found_result.fetchone()[0]  # always returns result

    def purge_ethereum_transaction_data(self) -> None:
        """Deletes all ethereum transaction related data from the DB"""
        with self.db.user_write() as cursor:
            cursor.executemany(
                'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
                [
                    (f'{RANGE_PREFIX_ETHTX}\\_%', '\\'),
                    (f'{RANGE_PREFIX_ETHINTERNALTX}\\_%', '\\'),
                    (f'{RANGE_PREFIX_ETHTOKENTX}\\_%', '\\'),
                ],
            )
            cursor.execute('DELETE FROM ethereum_transactions;')

    def get_transaction_hashes_no_receipt(
            self,
            tx_filter_query: Optional[ETHTransactionsFilterQuery],
            limit: Optional[int],
    ) -> List[EVMTxHash]:
        cursor = self.db.conn.cursor()
        querystr = 'SELECT DISTINCT tx_hash FROM ethereum_transactions '
        bindings = ()
        if tx_filter_query is not None:
            filter_query, bindings = tx_filter_query.prepare(with_order=False, with_pagination=False)  # type: ignore  # noqa: E501
            querystr += filter_query + ' AND '
        else:
            querystr += ' WHERE '

        querystr += 'tx_hash NOT IN (SELECT tx_hash from ethtx_receipts)'
        if limit is not None:
            querystr += 'LIMIT ?'
            bindings = (*bindings, limit)  # type: ignore

        cursor_result = cursor.execute(querystr, bindings)
        hashes = []
        for entry in cursor_result:
            try:
                hashes.append(deserialize_evm_tx_hash(entry[0]))
            except DeserializationError as e:
                log.debug(f'Got error {str(e)} while deserializing tx_hash {entry[0]} from the DB')

        return hashes

    def get_transaction_hashes_not_decoded(self, limit: Optional[int]) -> List[EVMTxHash]:
        cursor = self.db.conn.cursor()
        querystr = (
            'SELECT A.tx_hash from ethtx_receipts AS A LEFT OUTER JOIN evm_tx_mappings AS B '
            'ON A.tx_hash=B.tx_hash WHERE B.tx_hash is NULL'
        )
        bindings = ()
        if limit is not None:
            bindings = (limit,)  # type: ignore
            querystr += ' LIMIT ?'

        cursor.execute(querystr, bindings)
        return [make_evm_tx_hash(x[0]) for x in cursor]

    def add_receipt_data(  # pylint: disable=no-self-use
            self,
            write_cursor: 'DBCursor',
            data: Dict[str, Any],
    ) -> None:
        """Add tx receipt data as they are returned by the chain to the DB

        This assumes the transaction is already in the DB.

        May raise:
        - Key Error if any of the expected fields are missing
        - DeserializationError if there is a problem deserializing a value
        - pysqlcipher3.dbapi2.IntegrityError if the transaction hash is not in the DB:
        pysqlcipher3.dbapi2.IntegrityError: FOREIGN KEY constraint failed
        If the receipt already exists in the DB:
        pysqlcipher3.dbapi2.IntegrityError: UNIQUE constraint failed: ethtx_receipts.tx_hash
        """
        tx_hash_b = hexstring_to_bytes(data['transactionHash'])
        # some nodes miss the type field for older non EIP1559 transactions. So assume legacy (0)
        tx_type = hexstr_to_int(data.get('type', '0x0'))
        status = data.get('status', 1)  # status may be missing for older txs. Assume 1.
        if status is None:
            status = 1
        contract_address = deserialize_ethereum_address(data['contractAddress']) if data['contractAddress'] else None  # noqa: E501
        write_cursor.execute(
            'INSERT INTO ethtx_receipts (tx_hash, contract_address, status, type) '
            'VALUES(?, ?, ?, ?) ',
            (tx_hash_b, contract_address, status, tx_type),
        )

        log_tuples = []
        topic_tuples = []
        for log_entry in data['logs']:
            log_index = log_entry['logIndex']
            log_tuples.append((
                tx_hash_b,
                log_index,
                hexstring_to_bytes(log_entry['data']),
                deserialize_ethereum_address(log_entry['address']),
                int(log_entry['removed']),
            ))

            for idx, topic in enumerate(log_entry['topics']):
                topic_tuples.append((
                    tx_hash_b,
                    log_index,
                    hexstring_to_bytes(topic),
                    idx,
                ))

        if len(log_tuples) != 0:
            write_cursor.executemany(
                'INSERT INTO ethtx_receipt_logs (tx_hash, log_index, data, address, removed) '
                'VALUES(? ,? ,? ,? ,?)',
                log_tuples,
            )

            if len(topic_tuples) != 0:
                write_cursor.executemany(
                    'INSERT INTO ethtx_receipt_log_topics (tx_hash, log_index, topic, topic_index) '  # noqa: E501
                    'VALUES(? ,? ,?, ?)',
                    topic_tuples,
                )

    def get_receipt(self, cursor: 'DBCursor', tx_hash: EVMTxHash) -> Optional[EthereumTxReceipt]:  # pylint: disable=no-self-use  # noqa: E501
        cursor.execute('SELECT * from ethtx_receipts WHERE tx_hash=?', (tx_hash,))
        result = cursor.fetchone()
        if result is None:
            return None

        tx_receipt = EthereumTxReceipt(
            tx_hash=tx_hash,
            contract_address=result[1],
            status=bool(result[2]),  # works since value is either 0 or 1
            type=result[3],
        )

        cursor.execute('SELECT * from ethtx_receipt_logs WHERE tx_hash=?', (tx_hash,))
        with self.db.conn.read_ctx() as other_cursor:
            for result in cursor:
                log_index = result[1]
                tx_receipt_log = EthereumTxReceiptLog(
                    log_index=log_index,
                    data=result[2],
                    address=result[3],
                    removed=bool(result[4]),  # works since value is either 0 or 1
                )
                other_cursor.execute(
                    'SELECT topic from ethtx_receipt_log_topics WHERE tx_hash=? AND log_index=? '
                    'ORDER BY topic_index ASC',
                    (tx_hash, log_index),
                )
                for topic_result in other_cursor:
                    tx_receipt_log.topics.append(topic_result[0])

                tx_receipt.logs.append(tx_receipt_log)

        return tx_receipt

    def delete_transactions(self, write_cursor: 'DBCursor', address: ChecksumEvmAddress) -> None:
        """Delete all transactions related data to the given address from the DB

        So transactions, receipts, logs and decoded events
        """
        dbevents = DBHistoryEvents(self.db)
        write_cursor.executemany(
            'DELETE FROM used_query_ranges WHERE name=?;',
            [
                (f'{RANGE_PREFIX_ETHTX}_{address}',),
                (f'{RANGE_PREFIX_ETHINTERNALTX}_{address}',),
                (f'{RANGE_PREFIX_ETHTOKENTX}_{address}',),
            ],
        )
        # Get all tx_hashes that are touched by this address and no other address
        result = write_cursor.execute(
            'SELECT tx_hash from ethtx_address_mappings WHERE address=? AND tx_hash NOT IN ( '
            'SELECT tx_hash from ethtx_address_mappings WHERE address!=?'
            ')',
            (address, address),
        )
        tx_hashes = [make_evm_tx_hash(x[0]) for x in result]
        dbevents.delete_events_by_tx_hash(write_cursor, tx_hashes)
        # Now delete all relevant transactions. By deleting all relevant transactions all tables
        # are cleared thanks to cascading (except for history_events which was cleared above)
        write_cursor.executemany(
            'DELETE FROM ethereum_transactions WHERE tx_hash=? AND tx_hash NOT IN (SELECT event_identifier FROM history_events)',  # noqa: E501
            [(x,) for x in tx_hashes],
        )
        # Delete all remaining evm_tx_mappings so decoding can happen again for customized events
        write_cursor.executemany(
            'DELETE FROM evm_tx_mappings WHERE tx_hash=? AND blockchain=? AND value=?',
            [(x, 'ETH', HISTORY_MAPPING_DECODED) for x in tx_hashes],
        )

    def get_queried_range(self, cursor: 'DBCursor', address: ChecksumEvmAddress) -> Tuple[Timestamp, Timestamp]:  # noqa: E501
        """Gets the most conservative range that was queried for the ethereum
        transactions of an address.

        That means the least common denominator of normal, internal and token transactions
        """
        starts = []
        ends = []
        for prefix in (RANGE_PREFIX_ETHTX, RANGE_PREFIX_ETHTOKENTX, RANGE_PREFIX_ETHINTERNALTX):
            tx_range = self.db.get_used_query_range(cursor, f'{prefix}_{address}')
            if tx_range is None:  # if any range is missing then we gotta requery
                return Timestamp(0), Timestamp(0)

            starts.append(tx_range[0])
            ends.append(tx_range[1])

        return max(starts), min(ends)

    def get_max_genesis_trace_id(self) -> int:
        """Get the max trace id of genesis internal transactions from the database.
        If no internal transactions were found, returns 0 (zero)."""
        cursor = self.db.conn.cursor()
        trace_id, = cursor.execute(
            'SELECT MAX(trace_id) from ethereum_internal_transactions WHERE parent_tx_hash=?',
            (GENESIS_HASH,),
        ).fetchone()
        return trace_id if trace_id is not None else 0

    def get_or_create_genesis_transaction(
            self,
            account: ChecksumEvmAddress,
    ) -> EthereumTransaction:
        with self.db.conn.read_ctx() as cursor:
            tx_in_db = self.get_ethereum_transactions(
                cursor=cursor,
                filter_=ETHTransactionsFilterQuery.make(tx_hash=GENESIS_HASH, addresses=[account]),
                has_premium=True,
            )
        if len(tx_in_db) == 1:
            tx = tx_in_db[0]
        else:
            tx = EthereumTransaction(
                timestamp=ETHEREUM_BEGIN,
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
                self.add_ethereum_transactions(
                    write_cursor=cursor,
                    ethereum_transactions=[tx],
                    relevant_address=account,
                )
        return tx
