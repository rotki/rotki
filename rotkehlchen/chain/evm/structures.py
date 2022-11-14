import dataclasses
from typing import List, Optional

from rotkehlchen.types import ChainID, ChecksumEvmAddress, EVMTxHash


@dataclasses.dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class EvmTxReceiptLog:
    log_index: int
    data: bytes
    address: ChecksumEvmAddress
    removed: bool
    topics: List[bytes] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class EvmxTxReceipt:
    tx_hash: EVMTxHash
    chain_id: ChainID
    contract_address: Optional[ChecksumEvmAddress]
    status: bool
    type: int
    logs: List[EvmTxReceiptLog] = dataclasses.field(default_factory=list)
