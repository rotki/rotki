import logging
from typing import TYPE_CHECKING, Any, Optional

from rotkehlchen.chain.optimism.types import OptimismTransaction
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import OptimismTransactionsFilterQuery
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.types import ChainID, ChecksumEvmAddress, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor

from rotkehlchen.constants.limits import FREE_ETH_TX_LIMIT

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class DBOptimismTx(DBEvmTx):

    def add_optimism_transactions(
            self,
            write_cursor: 'DBCursor',
            optimism_transactions: list[OptimismTransaction],
            relevant_address: Optional[ChecksumEvmAddress],
    ) -> None:
        """Adds optimism transactions to the database"""
        self.add_evm_transactions(
            write_cursor,
            optimism_transactions,  # type: ignore[arg-type]
            relevant_address,
        )

        tx_tuples: list[tuple[Any, ...]] = []
        for tx in optimism_transactions:
            tx_tuples.append((
                tx.tx_hash,
                tx.chain_id.serialize_for_db(),
                tx.l1_fee,
            ))

        query = """
            INSERT INTO optimism_transactions(
              tx_hash,
              chain_id,
              l1_fee)
            VALUES (?, ?, ?)
        """
        self.db.write_tuples(
            write_cursor=write_cursor,
            tuple_type='evm_transaction',
            query=query,
            tuples=tx_tuples,
            relevant_address=relevant_address,
        )

    def get_optimism_transactions(
            self,
            cursor: 'DBCursor',
            filter_: OptimismTransactionsFilterQuery,
            has_premium: bool,
    ) -> list[OptimismTransaction]:
        """Returns a list of optimism transactions optionally filtered by
        the given filter query

        This function can raise:
        - pysqlcipher3.dbapi2.OperationalError if the SQL query fails due to invalid
        filtering arguments.
        """
        query, bindings = filter_.prepare()
        if has_premium:
            query = 'SELECT DISTINCT evm_transactions.tx_hash, evm_transactions.chain_id, timestamp, block_number, from_address, to_address, value, gas, gas_price, gas_used, input_data, nonce, l1_fee FROM (SELECT * FROM evm_transactions WHERE chain_id = 10) AS evm_transactions LEFT JOIN optimism_transactions on evm_transactions.tx_hash = optimism_transactions.tx_hash ' + query  # noqa: E501
            results = cursor.execute(query, bindings)
        else:
            query = 'SELECT DISTINCT evm_transactions.tx_hash, evm_transactions.chain_id, timestamp, block_number, from_address, to_address, value, gas, gas_price, gas_used, input_data, nonce, l1_fee FROM (SELECT * FROM evm_transactions WHERE chain_id = 10 ORDER BY timestamp DESC LIMIT ?) AS evm_transactions LEFT JOIN optimism_transactions on evm_transactions.tx_hash = optimism_transactions.tx_hash ' + query  # noqa: E501
            results = cursor.execute(query, [FREE_ETH_TX_LIMIT] + bindings)

        optimism_transactions = []
        for result in results:
            try:
                tx = OptimismTransaction(
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
                    l1_fee=int(result[12]),
                )
            except DeserializationError as e:
                self.db.msg_aggregator.add_error(
                    f'Error deserializing evm transaction from the DB. '
                    f'Skipping it. Error was: {e!s}',
                )
                continue

            optimism_transactions.append(tx)

        return optimism_transactions
