import dataclasses
from typing import NamedTuple

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EVMTxHash


@dataclasses.dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class EvmTxReceiptLog:
    log_index: int
    data: bytes
    address: ChecksumEvmAddress
    topics: list[bytes] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class EvmTxReceipt:
    tx_hash: EVMTxHash
    chain_id: ChainID
    contract_address: ChecksumEvmAddress | None
    status: bool  # False if the transaction failed
    tx_type: int
    logs: list[EvmTxReceiptLog] = dataclasses.field(default_factory=list)


class SwapData(NamedTuple):
    """Class that holds basic data for swaps"""
    from_asset: Asset
    from_amount: FVal
    to_asset: Asset
    to_amount: FVal
    fee_amount: FVal = ZERO
