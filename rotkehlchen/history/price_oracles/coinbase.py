from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.converters import asset_from_coinbase, asset_to_coinbase
from rotkehlchen.constants.assets import A_EUR, A_USD, A_USDC, A_USDT
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.coinbase import Coinbase
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.interfaces import HistoricalPriceOracleInterface
from rotkehlchen.types import Location, Price, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset, AssetWithOracles
    from rotkehlchen.exchanges.manager import ExchangeManager

COINBASE_CANDLE_GRANULARITY: Final = 'ONE_HOUR'
COINBASE_CANDLE_SECONDS: Final = 60 * 60


class CoinbaseHistoricalPriceOracle(HistoricalPriceOracleInterface):
    """Historical OHLC prices from a user's configured Coinbase connection."""

    def __init__(self, exchange_manager: ExchangeManager) -> None:
        super().__init__(oracle_name='coinbase')
        self.exchange_manager = exchange_manager

    def _get_coinbase(self) -> Coinbase | None:
        """Choose a connection deterministically without copying its credentials."""
        exchanges = self.exchange_manager.connected_exchanges.get(Location.COINBASE, ())
        return next((
            exchange for exchange in sorted(exchanges, key=lambda entry: entry.name)
            if isinstance(exchange, Coinbase)
        ), None)

    def can_query_history(
            self,
            from_asset: Asset,  # pylint: disable=unused-argument
            to_asset: Asset,  # pylint: disable=unused-argument
            timestamp: Timestamp,  # pylint: disable=unused-argument
            seconds: int | None = None,  # pylint: disable=unused-argument
    ) -> bool:
        return self._get_coinbase() is not None

    def query_current_price(
            self,
            from_asset: AssetWithOracles,  # pylint: disable=unused-argument
            to_asset: AssetWithOracles,  # pylint: disable=unused-argument
    ) -> Price:
        """Coinbase is intentionally exposed only as a historical price source."""
        return ZERO_PRICE

    @staticmethod
    def _select_candle(candles: list[dict[str, Any]], timestamp: Timestamp) -> Price | None:
        """Return the close of the hourly candle covering ``timestamp``."""
        for candle in candles:
            try:
                start = Timestamp(int(candle['start']))
                if start <= timestamp < start + COINBASE_CANDLE_SECONDS:
                    return deserialize_price(candle['close'])
            except (KeyError, TypeError, ValueError, DeserializationError):
                continue

        return None

    def query_historical_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        """Return the closing price of the Coinbase candle containing ``timestamp``.

        Direct pairs are preferred. If Coinbase only has a USD, EUR, USDC, or USDT pair,
        its close is converted to the requested quote through the historical-price pipeline.
        """
        if (coinbase := self._get_coinbase()) is None:
            raise PriceQueryUnsupportedAsset(from_asset.identifier)

        try:
            from_symbol = asset_to_coinbase(from_asset)
            to_symbol = asset_to_coinbase(to_asset)
        except UnknownAsset as e:
            raise PriceQueryUnsupportedAsset(e.identifier) from e

        quote_symbols = dict.fromkeys((
            to_symbol,
            asset_to_coinbase(A_USD),
            asset_to_coinbase(A_EUR),
            asset_to_coinbase(A_USDC),
            asset_to_coinbase(A_USDT),
        ))
        candle_start = Timestamp(timestamp - (timestamp % COINBASE_CANDLE_SECONDS))
        candle_end = Timestamp(candle_start + COINBASE_CANDLE_SECONDS - 1)

        for quote_symbol in quote_symbols:
            if quote_symbol == from_symbol:
                continue

            candles = coinbase.query_product_candles(
                product_id=f'{from_symbol}-{quote_symbol}',
                start=candle_start,
                end=candle_end,
                granularity=COINBASE_CANDLE_GRANULARITY,
                limit=1,
            )
            if (price := self._select_candle(candles=candles, timestamp=timestamp)) is None:
                continue
            if quote_symbol == to_symbol:
                return price

            try:
                quote_asset = asset_from_coinbase(quote_symbol, time=timestamp)
            except (UnknownAsset, DeserializationError):
                continue

            # Imported locally to avoid a module cycle with history.price.
            from rotkehlchen.history.price import PriceHistorian
            quote_rate = PriceHistorian().query_historical_price(
                from_asset=quote_asset,
                to_asset=to_asset,
                timestamp=timestamp,
            )
            return Price(price * quote_rate)

        raise NoPriceForGivenTimestamp(
            from_asset=from_asset,
            to_asset=to_asset,
            time=timestamp,
        )
