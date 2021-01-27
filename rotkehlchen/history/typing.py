from enum import Enum
from typing import TYPE_CHECKING, Union

from rotkehlchen.errors import DeserializationError

if TYPE_CHECKING:
    from rotkehlchen.externalapis.coingecko import Coingecko
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare


HistoricalPriceOracleInstance = Union['Coingecko', 'Cryptocompare']


class HistoricalPriceOracle(Enum):
    """Supported oracles for querying historical prices"""
    COINGECKO = 1
    CRYPTOCOMPARE = 2

    def __str__(self) -> str:
        if self == HistoricalPriceOracle.COINGECKO:
            return 'coingecko'
        if self == HistoricalPriceOracle.CRYPTOCOMPARE:
            return 'cryptocompare'
        raise AssertionError(f'Unexpected HistoricalPriceOracle: {self}')

    def serialize(self) -> str:
        return str(self)

    @classmethod
    def deserialize(cls, name: str) -> 'HistoricalPriceOracle':
        if name == 'coingecko':
            return cls.COINGECKO
        if name == 'cryptocompare':
            return cls.CRYPTOCOMPARE
        raise DeserializationError(f'Failed to deserialize historical price oracle: {name}')


DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER = [
    HistoricalPriceOracle.CRYPTOCOMPARE,
    HistoricalPriceOracle.COINGECKO,
]
