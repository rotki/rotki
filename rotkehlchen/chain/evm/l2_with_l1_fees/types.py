import typing
from typing import Any, Final, Literal

from rotkehlchen.errors.serialization import ConversionError
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EvmTransaction,
    EvmTransactionAuthorization,
    EVMTxHash,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.utils.misc import convert_to_int

# OP stack deposit transactions and Scroll L1 message transactions both use type 0x7e.
# They are submitted on L1 and relayed to L2, so the user already paid for the L1 side
# there and the L2 charges no L1 data fee: it is zero by definition. Receipts and indexers
# omit the fee field for them instead of reporting 0, which would otherwise look like an
# unresolved fee and send every lookup through all the indexers without ever resolving.
# https://specs.optimism.io/protocol/deposits.html
# https://docs.scroll.io/en/technology/chain/transactions/#l1-message-transactions
L1_ORIGINATED_TX_TYPE: Final = 0x7e

SupportedL2WithL1FeesType = Literal[
    SupportedBlockchain.OPTIMISM,
    SupportedBlockchain.BASE,
    SupportedBlockchain.SCROLL,
    SupportedBlockchain.INK,
]

L2ChainIdsWithL1FeesType = Literal[ChainID.OPTIMISM, ChainID.BASE, ChainID.SCROLL, ChainID.INK]
L2_CHAINIDS_WITH_L1_FEES: set[L2ChainIdsWithL1FeesType] = set(typing.get_args(L2ChainIdsWithL1FeesType))  # noqa: E501


def is_l1_originated_tx(raw_data: dict[str, Any] | None) -> bool:
    """Whether raw transaction or receipt data has the L1 originated type, whose L1 fee
    is always zero. See L1_ORIGINATED_TX_TYPE. Data without a type returns False."""
    if raw_data is None or (raw_type := raw_data.get('type')) is None:
        return False

    try:
        return convert_to_int(raw_type) == L1_ORIGINATED_TX_TYPE
    except ConversionError:
        return False


class L2WithL1FeesTransaction(EvmTransaction):  # noqa: PLW1641  # hash implemented by superclass
    """Represent a transaction with an L1 fee. """
    l1_fee: int | None
    tx_type: int

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
            l1_fee: int | None,
            tx_type: int = 0,
            db_id: int = -1,
            authorization_list: list[EvmTransactionAuthorization] | None = None,
    ):
        self.l1_fee = l1_fee
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
        if not isinstance(other, L2WithL1FeesTransaction):
            return False

        return hash(self) == hash(other)
