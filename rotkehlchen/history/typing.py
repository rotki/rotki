from enum import Enum
from typing import TYPE_CHECKING, NamedTuple, Union

from rotkehlchen.errors import DeserializationError

if TYPE_CHECKING:
    from rotkehlchen.externalapis.coingecko import Coingecko
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare


HistoricalPriceOracleInstance = Union['Coingecko', 'Cryptocompare']


class HistoricalPriceOracleProperties(NamedTuple):
    has_fiat_to_fiat: bool


class HistoricalPriceOracle(Enum):
    """Supported oracles for querying historical prices
    """
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

    def properties(self) -> HistoricalPriceOracleProperties:
        if self == HistoricalPriceOracle.COINGECKO:
            return HistoricalPriceOracleProperties(has_fiat_to_fiat=False)
        if self == HistoricalPriceOracle.CRYPTOCOMPARE:
            return HistoricalPriceOracleProperties(has_fiat_to_fiat=True)
        raise AssertionError(f'Unexpected HistoricalPriceOracle: {self}')


DEFAULT_HISTORICAL_PRICE_ORACLE_ORDER = [
    HistoricalPriceOracle.CRYPTOCOMPARE,
    HistoricalPriceOracle.COINGECKO,
]
