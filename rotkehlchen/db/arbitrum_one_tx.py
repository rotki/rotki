import logging
from typing import Any

from rotkehlchen.chain.arbitrum_one.types import ArbitrumOneTransaction
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.types import ChainID, deserialize_evm_tx_hash

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class DBArbitrumOneTx(DBEvmTx):

    def _build_evm_transaction(self, result: tuple[Any, ...]) -> ArbitrumOneTransaction:
        """Builds an arbitrum transaction

        May raise:
        - DeserializationError
        """
        tx_hash = deserialize_evm_tx_hash(result[0])
        chain_id = ChainID.deserialize_from_db(result[1])
        with self.db.conn.read_ctx() as cursor:
            tx_receipt = self.get_receipt(cursor, tx_hash, chain_id)
        if tx_receipt is None:
            raise DeserializationError(f'tx receipt for arbitrum one tx {tx_hash!s} does not exist in the database')  # noqa: E501

        return ArbitrumOneTransaction(
            tx_hash=tx_hash,
            chain_id=chain_id,
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
            tx_type=tx_receipt.type,
            db_id=result[12],
        )
