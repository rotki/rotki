from typing import TYPE_CHECKING, Optional

from rotkehlchen.types import EvmTransaction, EvmTransactionAuthorization

if TYPE_CHECKING:
    from rotkehlchen.types import ChainID, ChecksumEvmAddress, EVMTxHash, Timestamp


class ArbitrumOneTransaction(EvmTransaction):  # noqa: PLW1641  # hash implemented by superclass
    """Represents an Arbitrum One transaction"""
    tx_type: int

    def __init__(
            self,
            tx_hash: 'EVMTxHash',
            chain_id: 'ChainID',
            timestamp: 'Timestamp',
            block_number: int,
            from_address: 'ChecksumEvmAddress',
            to_address: Optional['ChecksumEvmAddress'],
            value: int,
            gas: int,
            gas_price: int,
            gas_used: int,
            input_data: bytes,
            nonce: int,
            tx_type: int,
            db_id: int = -1,
            authorization_list: list[EvmTransactionAuthorization] | None = None,
    ):
        self.tx_type = tx_type
        super().__init__(
            tx_hash=tx_hash,
            chain_id=chain_id,
            timestamp=timestamp,
            block_number=block_number,
            from_address=from_address,
            to_address=to_address,
            value=value,
            gas=gas,
            gas_price=gas_price,
            gas_used=gas_used,
            input_data=input_data,
            nonce=nonce,
            db_id=db_id,
            authorization_list=authorization_list,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ArbitrumOneTransaction):
            return False

        return hash(self) == hash(other)
