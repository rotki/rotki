import logging
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt, EthereumTxReceiptLog
from rotkehlchen.db.filtering import ETHTransactionsFilterQuery
from rotkehlchen.errors import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_ethereum_address,
    deserialize_timestamp,
)
from rotkehlchen.typing import EthereumTransaction
from rotkehlchen.utils.misc import hexstr_to_int, hexstring_to_bytes

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class DBEthTx():

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    def add_ethereum_transactions(self, ethereum_transactions: List[EthereumTransaction]) -> None:
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
            tuple_type='ethereum_transaction',
            query=query,
            tuples=tx_tuples,
        )

    def get_ethereum_transactions(
            self,
            filter_: ETHTransactionsFilterQuery,
    ) -> Tuple[List[EthereumTransaction], int]:
        """Returns a tuple with 2 entries.
        First entry is a list of ethereum transactions optionally filtered by
        time and/or from address and pagination.
        Second is the number of entries found for the current filter ignoring pagination.

        This function can raise:
        - pysqlcipher3.dbapi2.OperationalError if the SQL query fails due to invalid
        filtering arguments.
        """
        cursor = self.db.conn.cursor()
        query, bindings = filter_.prepare()
        query = 'SELECT * FROM ethereum_transactions ' + query
        results = cursor.execute(query, bindings)

        ethereum_transactions = []
        for result in results:
            try:
                tx = EthereumTransaction(
                    tx_hash=result[0],
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

        if filter_.pagination is not None:
            no_pagination_filter = deepcopy(filter_)
            no_pagination_filter.pagination = None
            query, bindings = no_pagination_filter.prepare()
            query = 'SELECT COUNT(*) FROM ethereum_transactions ' + query
            results = cursor.execute(query, bindings).fetchone()
            total_filter_count = results[0]
        else:
            total_filter_count = len(ethereum_transactions)

        return ethereum_transactions, total_filter_count

    def purge_ethereum_transaction_data(self) -> None:
        """Deletes all ethereum transaction related data from the DB"""
        cursor = self.db.conn.cursor()
        cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
            ('ethtxs\\_%', '\\'),
        )
        cursor.execute('DELETE FROM ethereum_transactions;')
        self.db.conn.commit()
        self.db.update_last_write()

    def add_receipt_data(self, data: Dict[str, Any]) -> None:
        """Add tx receipt data as they are returned by the chain to the DB

        This assumes the transaction is already in the DB.

        May raise:
        - Key Error if any of the expected fields are missing
        - DeserializationError if there is a problem deserializing a value
        - sqlcipher.DatabaseError if the transaction hash is not in the DB
          or if the receipt already exists in the DB. TODO: Differentiate?
        """
        tx_hash_b = hexstring_to_bytes(data['transactionHash'])
        # some nodes miss the type field for older non EIP1559 transactions. So assume legacy (0)
        tx_type = hexstr_to_int(data.get('type', '0x0'))
        cursor = self.db.conn.cursor()
        status = data.get('status', 1)  # status may be missing for older txs. Assume 1.
        if status is None:
            status = 1
        contract_address = deserialize_ethereum_address(data['contractAddress']) if data['contractAddress'] else None  # noqa: E501
        cursor.execute(
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
            cursor.executemany(
                'INSERT INTO ethtx_receipt_logs (tx_hash, log_index, data, address, removed) '
                'VALUES(? ,? ,? ,? ,?)',
                log_tuples,
            )

            if len(topic_tuples) != 0:
                cursor.executemany(
                    'INSERT INTO ethtx_receipt_log_topics (tx_hash, log_index, topic, topic_index) '  # noqa: E501
                    'VALUES(? ,? ,?, ?)',
                    topic_tuples,
                )

        self.db.conn.commit()
        self.db.update_last_write()

    def get_receipt(self, tx_hash: bytes) -> Optional[EthereumTxReceipt]:
        cursor = self.db.conn.cursor()
        results = cursor.execute('SELECT * from ethtx_receipts WHERE tx_hash=?', (tx_hash,))
        result = results.fetchone()
        if result is None:
            return None

        tx_receipt = EthereumTxReceipt(
            tx_hash=tx_hash,
            contract_address=result[1],
            status=bool(result[2]),  # works since value is either 0 or 1
            type=result[3],
        )

        results = cursor.execute('SELECT * from ethtx_receipt_logs WHERE tx_hash=?', (tx_hash,)).fetchall()  # noqa: E501
        # we do a fetchall since in each loop iteration another query of the cursor happens
        for result in results:
            log_index = result[1]
            tx_receipt_log = EthereumTxReceiptLog(
                log_index=log_index,
                data=result[2],
                address=result[3],
                removed=bool(result[4]),  # works since value is either 0 or 1
            )
            topic_results = cursor.execute(
                'SELECT topic from ethtx_receipt_log_topics WHERE tx_hash=? AND log_index=? '
                'ORDER BY topic_index ASC',
                (tx_hash, log_index),
            )
            for topic_result in topic_results:
                tx_receipt_log.topics.append(topic_result[0])

            tx_receipt.logs.append(tx_receipt_log)

        return tx_receipt
