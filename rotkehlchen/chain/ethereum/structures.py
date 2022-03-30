import dataclasses
from typing import List, Optional

from rotkehlchen.types import ChecksumEthAddress, EVMTxHash


@dataclasses.dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class EthereumTxReceiptLog:
    log_index: int
    data: bytes
    address: ChecksumEthAddress
    removed: bool
    topics: List[bytes] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class EthereumTxReceipt:
    tx_hash: EVMTxHash
    contract_address: Optional[ChecksumEthAddress]
    status: bool
    type: int
    logs: List[EthereumTxReceiptLog] = dataclasses.field(default_factory=list)
