import typing
from typing import Literal

from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EvmTransaction,
    EVMTxHash,
    SupportedBlockchain,
    Timestamp,
)

SupportedL2WithL1FeesType = Literal[
    SupportedBlockchain.OPTIMISM,
    SupportedBlockchain.BASE,
    SupportedBlockchain.SCROLL,
]

L2ChainIdsWithL1FeesType = Literal[ChainID.OPTIMISM, ChainID.BASE, ChainID.SCROLL]
L2_CHAINIDS_WITH_L1_FEES: set[L2ChainIdsWithL1FeesType] = set(typing.get_args(L2ChainIdsWithL1FeesType))  # noqa: E501


class L2WithL1FeesTransaction(EvmTransaction):  # noqa: PLW1641  # hash implemented by superclass
    """Represent a transaction with an L1 fee. """
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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, L2WithL1FeesTransaction):
            return False

        return hash(self) == hash(other)
