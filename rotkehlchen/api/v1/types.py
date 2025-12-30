from dataclasses import dataclass
from enum import auto
from typing import TYPE_CHECKING, Literal

from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.utils.mixins.enums import SerializableEnumNameMixin

if TYPE_CHECKING:
    from rotkehlchen.types import Location


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class IncludeExcludeFilterData:
    values: list[HistoryBaseEntryType]
    operator: Literal['IN', 'NOT IN'] = 'IN'


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class IncludeExcludeStringFilterData:
    """Filter data for string values with include/exclude behaviour."""
    values: list[str]
    operator: Literal['IN', 'NOT IN'] = 'IN'


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class IncludeExcludeIntegerFilterData:
    """Filter data for integer values with include/exclude behaviour."""
    values: list[int]
    operator: Literal['IN', 'NOT IN'] = 'IN'


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class IncludeExcludeSingleStringFilterData:
    """Filter data for a single string value with include/exclude behaviour."""
    value: str
    operator: Literal['=', '!='] = '='


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class IncludeExcludeSingleLocationFilterData:
    """Filter data for a single location value with include/exclude behaviour."""
    value: 'Location'
    operator: Literal['=', '!='] = '='


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
