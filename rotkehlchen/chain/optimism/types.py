from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTransaction, EVMTxHash, Timestamp

if TYPE_CHECKING:
    # This is a list of all optimism abis that are guaranteed to be returned
    # by EthereumContracts as they are stored in the file/DB
    OPTIMISM_KNOWN_ABI = Literal['VELO_V2_LP']


class OptimismTransaction(EvmTransaction):  # noqa: PLW1641  # hash implemented by superclass
    """Represent an Optimism transaction"""
    l1_fee: int

    def __init__(
            self,
            tx_hash: EVMTxHash,
            chain_id: ChainID,
            timestamp: Timestamp,
            block_number: int,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress | None,
            value: int,
            gas: int,
            gas_price: int,
            gas_used: int,
            input_data: bytes,
            nonce: int,
            l1_fee: int,
            db_id: int = -1,
    ):
        self.l1_fee = l1_fee
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
        )

    def serialize(self) -> dict[str, Any]:
        result = super().serialize()
        result['l1_fee'] = str(result['l1_fee'])
        return result

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OptimismTransaction):
            return False

        return hash(self) == hash(other)
