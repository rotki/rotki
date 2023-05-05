from dataclasses import dataclass
from typing import Literal, Optional, TypedDict

from rotkehlchen.accounting.structures.base import HistoryBaseEntryType
from rotkehlchen.types import SUPPORTED_CHAIN_IDS, ChecksumEvmAddress, EVMTxHash


class EvmTransactionDecodingApiData(TypedDict):
    evm_chain: SUPPORTED_CHAIN_IDS
    tx_hashes: Optional[list[EVMTxHash]]


class EvmPendingTransactionDecodingApiData(TypedDict):
    evm_chain: SUPPORTED_CHAIN_IDS
    addresses: Optional[list[ChecksumEvmAddress]]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class IncludeExcludeFilterData:
    values: list[HistoryBaseEntryType]
    behaviour: Literal['IN', 'NOT IN'] = 'IN'
