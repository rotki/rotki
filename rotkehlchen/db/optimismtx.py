import logging
from typing import TYPE_CHECKING, Any, Optional

from rotkehlchen.chain.optimism.types import OptimismTransaction
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.types import ChainID, ChecksumEvmAddress, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor

from rotkehlchen.constants.limits import FREE_ETH_TX_LIMIT

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class DBOptimismTx(DBEvmTx):

    def add_evm_transactions(
            self,
            write_cursor: 'DBCursor',
            evm_transactions: list[OptimismTransaction],  # type: ignore[override]
            relevant_address: Optional[ChecksumEvmAddress],
    ) -> None:
        """Adds optimism transactions to the database"""
        super().add_evm_transactions(
            write_cursor,
            evm_transactions,  # type: ignore[arg-type]
            relevant_address,
        )

        tx_tuples: list[tuple[Any, ...]] = []
        for tx in evm_transactions:
            tx_tuples.append((
                tx.tx_hash,
                tx.l1_fee,
            ))

        query = """
            INSERT INTO optimism_transactions(
              tx_hash,
              l1_fee)
            VALUES (?, ?)
        """
        self.db.write_tuples(
            write_cursor=write_cursor,
            tuple_type='evm_transaction',
            query=query,
            tuples=tx_tuples,
        )

    def _form_evm_transaction_dbquery(self, query: str, bindings: list[Any], has_premium: bool) -> tuple[str, list[tuple]]:  # noqa: E501
        if has_premium:
            return (
                'SELECT DISTINCT evm_transactions.tx_hash, evm_transactions.chain_id, evm_transactions.timestamp, evm_transactions.block_number, evm_transactions.from_address, evm_transactions.to_address, evm_transactions.value, evm_transactions.gas, evm_transactions.gas_price, evm_transactions.gas_used, evm_transactions.input_data, evm_transactions.nonce, OP.l1_fee FROM evm_transactions LEFT JOIN optimism_transactions AS OP ON evm_transactions.tx_hash=OP.tx_hash ' + query,  # noqa: E501
                bindings,
            )
        # else
        return (
            'SELECT DISTINCT evm_transactions.tx_hash, evm_transactions.chain_id, evm_transactions.timestamp, evm_transactions.block_number, evm_transactions.from_address, evm_transactions.to_address, evm_transactions.value, evm_transactions.gas, evm_transactions.gas_price, evm_transactions.gas_used, evm_transactions.input_data, evm_transactions.nonce, OP.l1_fee FROM (SELECT * FROM evm_transactions ORDER BY timestamp DESC LIMIT ?) AS evm_transactions LEFT JOIN optimism_transactions AS OP ON evm_transactions.tx_hash=OP.tx_hash ' + query,  # noqa: E501
            [FREE_ETH_TX_LIMIT] + bindings,
        )

    def _build_evm_transaction(self, result: tuple[Any, ...]) -> OptimismTransaction:
        return OptimismTransaction(
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
