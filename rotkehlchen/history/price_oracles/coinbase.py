from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.constants.assets import A_EUR, A_USD, A_USDC, A_USDT
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.coinbase import Coinbase
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.interfaces import HistoricalPriceOracleInterface
from rotkehlchen.types import Location, Price, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
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
            resolved_from_asset = (
                from_asset if isinstance(from_asset, AssetWithOracles)
                else from_asset.resolve_to_asset_with_oracles()
            )
            resolved_to_asset = (
                to_asset if isinstance(to_asset, AssetWithOracles)
                else to_asset.resolve_to_asset_with_oracles()
            )
            quote_assets = tuple(dict.fromkeys((
                resolved_to_asset,
                A_USD.resolve_to_asset_with_oracles(),
                A_EUR.resolve_to_asset_with_oracles(),
                A_USDC.resolve_to_asset_with_oracles(),
                A_USDT.resolve_to_asset_with_oracles(),
            )))
        except (UnknownAsset, WrongAssetType) as e:
            raise PriceQueryUnsupportedAsset(from_asset.identifier) from e

        asset_symbols = GlobalDBHandler.get_location_asset_symbols(
            assets=[resolved_from_asset, *quote_assets],
            location=Location.COINBASE,
        )
        if len(from_symbols := asset_symbols[resolved_from_asset]) == 0:
            raise PriceQueryUnsupportedAsset(from_asset.identifier)

        products = coinbase.query_spot_products()
        candle_start = Timestamp(timestamp - (timestamp % COINBASE_CANDLE_SECONDS))
        candle_end = Timestamp(candle_start + COINBASE_CANDLE_SECONDS - 1)

        for quote_asset in quote_assets:
            if quote_asset == resolved_from_asset:
                continue
            quote_symbols = asset_symbols[quote_asset]
            product_id = next((
                product_id
                for (base_symbol, quote_symbol), product_id in products.items()
                if base_symbol in from_symbols and quote_symbol in quote_symbols
            ), None)
            if product_id is None:
                continue

            candles = coinbase.query_product_candles(
                product_id=product_id,
                start=candle_start,
                end=candle_end,
                granularity=COINBASE_CANDLE_GRANULARITY,
                limit=1,
            )
            if (price := self._select_candle(candles=candles, timestamp=timestamp)) is None:
                continue
            if quote_asset == resolved_to_asset:
                return price

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
