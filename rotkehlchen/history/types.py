from typing import TYPE_CHECKING, NamedTuple, Union

from rotkehlchen.assets.asset import Asset
from rotkehlchen.types import OracleSource, Price, Timestamp
from rotkehlchen.utils.mixins.enums import DBCharEnumMixIn

from .deserialization import deserialize_price

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.oracles.uniswap import UniswapV2Oracle, UniswapV3Oracle
    from rotkehlchen.externalapis.alchemy import Alchemy
    from rotkehlchen.externalapis.coingecko import Coingecko
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare
    from rotkehlchen.externalapis.defillama import Defillama
    from rotkehlchen.externalapis.yahoofinance import YahooFinance

HistoricalPriceOracleInstance = Union['Coingecko', 'Cryptocompare', 'Defillama', 'Alchemy', 'UniswapV2Oracle', 'UniswapV3Oracle', 'YahooFinance']  # noqa: E501


class HistoricalPriceOracle(DBCharEnumMixIn, OracleSource):
    """Supported oracles for querying historical prices"""
    MANUAL = 1
    COINGECKO = 2
    CRYPTOCOMPARE = 3
    XRATESCOM = 4
    MANUAL_CURRENT = 5
    DEFILLAMA = 6
    UNISWAPV2 = 7
    UNISWAPV3 = 8
    ALCHEMY = 9
    YAHOOFINANCE = 10


NOT_EXPOSED_SOURCES = (
    HistoricalPriceOracle.XRATESCOM,
)

DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER = (
    HistoricalPriceOracle.CRYPTOCOMPARE,
    HistoricalPriceOracle.COINGECKO,
    HistoricalPriceOracle.DEFILLAMA,
    HistoricalPriceOracle.UNISWAPV3,
    HistoricalPriceOracle.UNISWAPV2,
)


class HistoricalPrice(NamedTuple):
    """A historical price entry"""
    from_asset: Asset
    to_asset: Asset
    source: HistoricalPriceOracle
    timestamp: Timestamp
    price: Price

    def __str__(self) -> str:
        return (
            f'Price entry {self.price!s} of {self.from_asset} -> {self.to_asset} '
            f'at {self.timestamp} from {self.source!s}'
        )

    def serialize_for_db(self) -> tuple[str, str, str, int, str]:
        return (
            self.from_asset.identifier,
            self.to_asset.identifier,
            self.source.serialize_for_db(),
            self.timestamp,
            str(self.price),
        )

    @classmethod
    def deserialize_from_db(cls, value: tuple[str, str, str, int, str]) -> 'HistoricalPrice':
        """Deserialize a HistoricalPrice entry from the DB.

        May raise:
        - DeserializationError
        - UnknownAsset
        """
        return cls(
            from_asset=Asset(value[0]).check_existence(),
            to_asset=Asset(value[1]).check_existence(),
            source=HistoricalPriceOracle.deserialize_from_db(value[2]),
            timestamp=Timestamp(value[3]),
            price=deserialize_price(value[4]),
        )
