from typing import TYPE_CHECKING, NamedTuple, Tuple, Union

from rotkehlchen.assets.asset import Asset
from rotkehlchen.typing import Price, Timestamp
from rotkehlchen.utils.mixins.dbenum import DBEnumMixIn

from .deserialization import deserialize_price

if TYPE_CHECKING:
    from rotkehlchen.externalapis.coingecko import Coingecko
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare


HistoricalPriceOracleInstance = Union['Coingecko', 'Cryptocompare']


class HistoricalPriceOracle(DBEnumMixIn):
    """Supported oracles for querying historical prices"""
    MANUAL = 1
    COINGECKO = 2
    CRYPTOCOMPARE = 3
    XRATESCOM = 4


NOT_EXPOSED_SOURCES = (
    HistoricalPriceOracle.XRATESCOM,
)

DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER = [
    HistoricalPriceOracle.MANUAL,
    HistoricalPriceOracle.CRYPTOCOMPARE,
    HistoricalPriceOracle.COINGECKO,
]


class HistoricalPrice(NamedTuple):
    """A historical price entry"""
    from_asset: Asset
    to_asset: Asset
    source: HistoricalPriceOracle
    timestamp: Timestamp
    price: Price

    def __str__(self) -> str:
        return (
            f'Price entry {str(self.price)} of {self.from_asset} -> {self.to_asset} '
            f'at {self.timestamp} from {str(self.source)}'
        )

    def serialize_for_db(self) -> Tuple[str, str, str, int, str]:
        return (
            self.from_asset.identifier,
            self.to_asset.identifier,
            self.source.serialize_for_db(),
            self.timestamp,
            str(self.price),
        )

    @classmethod
    def deserialize_from_db(cls, value: Tuple[str, str, str, int, str]) -> 'HistoricalPrice':
        """Deserialize a HistoricalPrice entry from the DB.

        May raise:
        - DeserializationError
        - UnknownAsset
        """
        return cls(
            from_asset=Asset(value[0]),
            to_asset=Asset(value[1]),
            source=HistoricalPriceOracle.deserialize_from_db(value[2]),
            timestamp=Timestamp(value[3]),
            price=deserialize_price(value[4]),
        )
