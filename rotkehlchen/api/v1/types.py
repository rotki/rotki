from dataclasses import dataclass
from enum import auto
from typing import Literal, TypedDict

from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.types import SUPPORTED_CHAIN_IDS, EVMTxHash
from rotkehlchen.utils.mixins.enums import SerializableEnumNameMixin


class EvmTransactionDecodingApiData(TypedDict):
    evm_chain: SUPPORTED_CHAIN_IDS
    tx_hashes: list[EVMTxHash] | None


class EvmPendingTransactionDecodingApiData(TypedDict):
    evm_chain: SUPPORTED_CHAIN_IDS


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class IncludeExcludeFilterData:
    values: list[HistoryBaseEntryType]
    operator: Literal['IN', 'NOT IN'] = 'IN'


class ModuleWithBalances(SerializableEnumNameMixin):
    """Used to validate the used module to query stats at the API balance endpoint"""
    UNISWAP = auto()
    SUSHISWAP = auto()
    BALANCER = auto()


class ModuleWithStats(SerializableEnumNameMixin):
    """Used to validate the used module to query stats at the API stats endpoint"""
    AAVE = auto()
    COMPOUND = auto()
    LIQUITY = auto()
    UNISWAP = auto()
    SUSHISWAP = auto()
    BALANCER = auto()
