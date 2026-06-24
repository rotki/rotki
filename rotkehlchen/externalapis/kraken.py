import logging
from http import HTTPStatus
from typing import Any, Final

import requests

from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.constants import ONE
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.interfaces import CurrentPriceOracleInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location, Price, Timestamp
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.network import create_session

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
KRAKEN_API_URL: Final = 'https://api.kraken.com/0/public/Ticker'
# Kraken's public Ticker endpoint returns every market in a single response.
# Cache it for a few minutes so that repeated current-price queries don't
# re-download the ~hundreds of KB payload on every call.
KRAKEN_TICKERS_CACHE_SECS: Final = 300


class Kraken(CurrentPriceOracleInterface):
    def __init__(self) -> None:
        super().__init__(oracle_name='kraken')
        self.session = create_session()
        self.session.headers.update({'User-Agent': 'rotkehlchen'})
        self._tickers_cache: dict[str, Any] = {}
        self._tickers_cache_ts: Timestamp = Timestamp(0)

    def _query_ticker(self) -> dict[str, Any]:
        """Query Kraken's public Ticker endpoint for every market.

        The ``assetVersion=1`` parameter is required so that the returned
        market keys use the ``BASE/QUOTE`` notation (e.g. ``BTC/USD``) that
        :meth:`_maybe_split_pair` relies on. Other versions return
        concatenated keys (``XXBTZUSD``) which we can't split reliably.

        May raise:
        - RemoteError if the query fails or Kraken returns errors.
        """
        try:
            response = self.session.get(
                url=KRAKEN_API_URL,
                params={'assetVersion': 1},
                timeout=CachedSettings().get_timeout_tuple(),
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Kraken API request failed due to {e!s}') from e

        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            self.last_rate_limit = ts_now()
            raise RemoteError(
                message='Got rate limited by Kraken querying ticker prices',
                error_code=HTTPStatus.TOO_MANY_REQUESTS,
            )

        if response.status_code != HTTPStatus.OK:
            raise RemoteError(
                f'Kraken ticker query failed with HTTP status code: {response.status_code}',
            )

        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError as e:
            raise RemoteError(f'Invalid JSON in Kraken ticker response. {e!s}') from e

        if not isinstance(data, dict):
            raise RemoteError(f'Kraken ticker response was not a JSON object: {data}')

        if len(errors := data.get('error', [])) != 0:
            raise RemoteError(f'Kraken ticker query failed with errors: {errors}')
        if not isinstance(result := data.get('result'), dict):
            raise RemoteError(f'Kraken ticker response is missing a result object: {data}')

        return result

    def _get_tickers(self) -> dict[str, Any]:
        """Return all Kraken tickers, cached for ``KRAKEN_TICKERS_CACHE_SECS``.

        May raise:
        - RemoteError if the underlying query fails.
        """
        if (
            self._tickers_cache and
            ts_now() - self._tickers_cache_ts <= KRAKEN_TICKERS_CACHE_SECS
        ):
            return self._tickers_cache

        result = self._query_ticker()
        self._tickers_cache = result
        self._tickers_cache_ts = ts_now()
        return result

    @staticmethod
    def _asset_to_kraken_symbols(asset: AssetWithOracles) -> set[str]:
        """Return possible Kraken symbols for an asset.

        Only Kraken-specific location asset mappings are consulted. Generic
        mappings (NULL location) are intentionally ignored since they come
        from other exchanges and would let an unrelated Kraken market match
        the asset.
        """
        symbols = {'BTC' if asset.symbol == 'XBT' else asset.symbol}
        with GlobalDBHandler().conn.read_ctx() as cursor:
            symbols.update(row[0] for row in cursor.execute(
                'SELECT exchange_symbol FROM location_asset_mappings '
                'WHERE local_id=? AND location=?',
                (asset.identifier, Location.KRAKEN.serialize_for_db()),
            ))

        return symbols

    @staticmethod
    def _get_price_from_ticker(ticker: Any) -> Price:
        """Deserialize the last closed trade price from a Kraken ticker entry."""
        if (
                not isinstance(ticker, dict) or
                not isinstance(closed_trade := ticker.get('c'), list) or
                len(closed_trade) == 0
        ):
            return ZERO_PRICE

        try:
            return deserialize_price(closed_trade[0])
        except DeserializationError as e:
            log.debug('Could not deserialize Kraken ticker price %s: %s', closed_trade, e)
            return ZERO_PRICE

    @staticmethod
    def _maybe_split_pair(pair: str) -> tuple[str, str] | None:
        if '/' not in pair:
            return None

        base, quote = pair.split('/', maxsplit=1)
        return base, quote

    def query_current_price(
            self,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
    ) -> Price:
        """Query a single current price from Kraken.

        May raise:
        - RemoteError if there is a problem querying Kraken.
        """
        return self.query_multiple_current_prices(
            from_assets=[from_asset],
            to_asset=to_asset,
        ).get(from_asset, ZERO_PRICE)

    def query_multiple_current_prices(
            self,
            from_assets: list[AssetWithOracles],
            to_asset: AssetWithOracles,
    ) -> dict[AssetWithOracles, Price]:
        """Query current prices from Kraken.

        A single request to the public Ticker endpoint returns every Kraken
        market; the response is cached for a few minutes and the requested
        pairs are filtered locally. This avoids the previous approach of
        building a per-asset ``pair`` query, which could send an invalid pair
        and cause Kraken to reject the whole batch with ``EQuery:Unknown
        asset pair``.

        May raise:
        - RemoteError if there is a problem querying Kraken.
        """
        if len(from_assets) == 0:
            return {}
        if to_asset in from_assets:
            prices: dict[AssetWithOracles, Price] = {to_asset: Price(ONE)}
            from_assets = [asset for asset in from_assets if asset != to_asset]
            if len(from_assets) == 0:
                return prices
        else:
            prices = {}

        requested_asset_symbols: dict[str, set[AssetWithOracles]] = {}
        for asset in from_assets:
            for symbol in self._asset_to_kraken_symbols(asset):
                requested_asset_symbols.setdefault(symbol, set()).add(asset)

        to_asset_symbols = self._asset_to_kraken_symbols(to_asset)
        ticker_data = self._get_tickers()

        for pair, ticker in ticker_data.items():
            if not isinstance(pair, str) or (symbols := self._maybe_split_pair(pair)) is None:
                continue

            base_symbol, quote_symbol = symbols
            if (
                    quote_symbol in to_asset_symbols and
                    (matching_assets := requested_asset_symbols.get(base_symbol)) is not None and
                    (price := self._get_price_from_ticker(ticker)) != ZERO_PRICE
            ):
                for asset in matching_assets:
                    prices[asset] = price
            elif (
                    base_symbol in to_asset_symbols and
                    (matching_assets := requested_asset_symbols.get(quote_symbol)) is not None and
                    (price := self._get_price_from_ticker(ticker)) != ZERO_PRICE
            ):
                for asset in matching_assets:
                    prices[asset] = Price(ONE / price)

        if len(prices) == 0:
            log.debug('Kraken could not find prices for %s to %s', from_assets, to_asset)

        return prices
