from typing import TYPE_CHECKING, Union

from rotkehlchen.errors import DeserializationError
from rotkehlchen.utils.mixins import DBEnumMixIn

if TYPE_CHECKING:
    from rotkehlchen.externalapis.coingecko import Coingecko
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare


HistoricalPriceOracleInstance = Union['Coingecko', 'Cryptocompare']


class HistoricalPriceOracle(DBEnumMixIn):
    """Supported oracles for querying historical prices"""
    MANUAL = 1
    COINGECKO = 2
    CRYPTOCOMPARE = 3

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
