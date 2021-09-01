import logging
from typing import TYPE_CHECKING, Any, List, Tuple

from rotkehlchen.db.filtering import ETHTransactionsFilterQuery
from rotkehlchen.errors import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.typing import EthereumTransaction

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class DBEthTx():

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    def add_ethereum_transactions(
            self,
            ethereum_transactions: List[EthereumTransaction],
            from_etherscan: bool,
    ) -> None:
        """Adds ethereum transactions to the database

        If from_etherscan is True then this means that the source of the transactions
        is an etherscan query. This is used to determine how we should handle the
        transactions with nonce "-1" as this is how we currently identify internal
        ethereum transactions from etherscan.
        """
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
            from_etherscan=from_etherscan,
        )

    def get_ethereum_transactions(
            self,
            filter_: ETHTransactionsFilterQuery,
    ) -> List[EthereumTransaction]:
        """Returns a list of ethereum transactions optionally filtered by time and/or from address

        The returned list is ordered from oldest to newest
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

        return ethereum_transactions

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
