import json
import logging
from http import HTTPStatus
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.timing import DAY_IN_SECONDS, DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.interfaces import HistoricalPriceOracleInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price, Timestamp
from rotkehlchen.utils.misc import create_timestamp, timestamp_to_date, ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class DefiLlama(HistoricalPriceOracleInterface):

    def __init__(self) -> None:
        super().__init__(oracle_name='defillama')
        self.session = requests.session()
        self.session.headers.update({'User-Agent': 'rotkehlchen'})
        self.all_coins_cache: Optional[Dict[str, Dict[str, Any]]] = None
        self.last_rate_limit = 0

    def _query(
            self,
            module: str,
            subpath: Optional[str] = None,
            options: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Performs a defillama query

        May raise:
        - RemoteError if there is a problem querying defillama
        """
        if options is None:
            options = {}
        url = f'https://coins.llama.fi/{module}/'
        if subpath:
            url += subpath

        log.debug(f'Querying defillama: {url}?{urlencode(options)}')
        try:
            response = self.session.get(
                f'{url}?{urlencode(options)}',
                timeout=DEFAULT_TIMEOUT_TUPLE,
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'DefiLlama API request failed due to {str(e)}') from e

        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            self.last_rate_limit = ts_now()
            msg = f'Got rate limited by coingecko querying {url}'
            log.warning(msg)
            raise RemoteError(message=msg, error_code=HTTPStatus.TOO_MANY_REQUESTS)

        if response.status_code != 200:
            msg = (
                f'DefiLlama API request {response.url} failed with HTTP status '
                f'code: {response.status_code}'
            )
            raise RemoteError(msg)

        try:
            decoded_json = json.loads(response.text)
        except json.decoder.JSONDecodeError as e:
            msg = f'Invalid JSON in Coingecko response. {e}'
            raise RemoteError(msg) from e

        return decoded_json

    def _get_asset_id(self, asset: AssetWithOracles) -> Optional[str]:
        """
        Create the id to be used in DefiLlama.
        May raise:
        - UnsupportedAsset
        """
        if asset.is_evm_token() is True:
            asset = asset.resolve_to_evm_token()
            return f'{str(asset.chain)}:{asset.evm_address}'

        return f'coingecko:{asset.to_coingecko()}'

    def query_current_price(
            self,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
    ) -> Price:
        """
        Returns a simple price for from_asset to to_asset in DefiLlama.

        from_asset can only be an evm token since DefiLlama doesn't track any other type
        of assets

        May raise:
        - RemoteError if there is a problem querying coingecko
        """
        try:
            coin_id = self._get_asset_id(from_asset)
        except UnsupportedAsset:
            log.warning(
                f'Tried to query current price using DefiLlama from {from_asset} to '
                f'{to_asset} but {from_asset} is not an EVM token and is not '
                f'suppoorted by coingecko',
            )
            return Price(ZERO)

        result = self._query(
            module='prices',
            subpath=f'current/{coin_id}',
        )

        if 'coins' not in result or len(result['coins']) == 0:
            log.warning(
                f'Queried DefiLlama current price from {from_asset.identifier} '
                f'to {to_asset.identifier}. But coins ins not available in the result {result}',
            )
            return Price(ZERO)

        coin_result_raw = result['coins'][coin_id]
        try:
            if (
                'confidence' in coin_result_raw and
                FVal(coin_result_raw['confidence']) < FVal('0.20')
            ):
                # DefiLlama provides a confidence value ranking how good they measure the price
                # is. When their confidence in the price is lower than 20% ignore it. Probably a
                # spam token
                return Price(ZERO)
            usd_price = Price(FVal(coin_result_raw['price']))
        except KeyError as e:
            log.warning(
                f'Queried DefiLlama simple price from {from_asset.identifier} '
                f'to {to_asset.identifier}. But got key error for {str(e)} when '
                f'processing the result.',
            )
            return Price(ZERO)

        # We got the price in usd but if that is not what we need we should query for the next
        # step in the chain of prices
        if to_asset == A_USD:
            return usd_price

        rate_price = Inquirer().find_price(from_asset=A_USD, to_asset=to_asset)
        return Price(usd_price * rate_price)

    def can_query_history(  # pylint: disable=no-self-use
            self,
            from_asset: Asset,  # pylint: disable=unused-argument
            to_asset: Asset,  # pylint: disable=unused-argument
            timestamp: Timestamp,  # pylint: disable=unused-argument
            seconds: Optional[int] = None,  # pylint: disable=unused-argument
    ) -> bool:
        return True  # noop for DefiLlama

    def rate_limited_in_last(
            self,
            seconds: Optional[int] = None,
    ) -> bool:
        if seconds is None:
            return False

        return ts_now() - self.last_rate_limit <= seconds

    def query_historical_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        """
        May raise:
        - PriceQueryUnsupportedAsset if either from_asset or to_asset are not supported
        - NoPriceForGivenTimestamp if no price could be found
        """
        try:
            from_asset = from_asset.resolve_to_asset_with_oracles()
            to_asset = to_asset.resolve_to_asset_with_oracles()
        except UnknownAsset as e:
            raise PriceQueryUnsupportedAsset(e.identifier) from e

        # check DB cache
        price_cache_entry = GlobalDBHandler().get_historical_price(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
            max_seconds_distance=DAY_IN_SECONDS,
            source=HistoricalPriceOracle.DEFILLAMA,
        )
        if price_cache_entry:
            return price_cache_entry.price

        try:
            coin_id = self._get_asset_id(from_asset)
        except UnsupportedAsset as e:
            log.warning(
                f'Tried to query historical price using DefiLlama from {from_asset} to '
                f'{to_asset} at {timestamp} but {from_asset} is not an EVM token and is not '
                f'suppoorted by coingecko',
            )
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
                rate_limited=False,
            ) from e

        # no cache, query coingecko for daily price
        date = timestamp_to_date(timestamp, formatstr='%d-%m-%Y')
        result = self._query(
            module='prices',
            subpath=f'historical/{timestamp}/{coin_id}',
        )

        if 'coins' not in result or len(result['coins']) == 0:
            log.warning(
                f'Queried DefiLlama current price from {from_asset.identifier} '
                f'to {to_asset.identifier}. But coins ins not available in the result {result}',
            )
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
                rate_limited=False,
            )

        coin_result_raw = result['coins'][coin_id]
        try:
            if (
                'confidence' in coin_result_raw and
                FVal(coin_result_raw['confidence']) < FVal('0.20')
            ):
                # DefiLlama provides a confidence value ranking how good they measure the price
                # is. When their confidence in the price is lower than 20% ignore it. Probably a
                # spam token
                return Price(ZERO)
            usd_price = Price(FVal(coin_result_raw['price']))
        except KeyError as e:
            log.warning(
                f'Queried DefiLlama simple price from {from_asset.identifier} '
                f'to {to_asset.identifier}. But got key error for {str(e)} when '
                f'processing the result. {result}',
            )
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
                rate_limited=False,
            ) from e

        if to_asset != A_USD:
            # We need to query intermediate price in this case. Let the error propagate if
            # any happens in this subcall
            to_asset_price = PriceHistorian().query_historical_price(
                from_asset=A_USD,
                to_asset=to_asset,
                timestamp=timestamp,
            )
            price = Price(usd_price * to_asset_price)
        else:
            price = usd_price

        # save result in the DB and return
        date_timestamp = create_timestamp(date, formatstr='%d-%m-%Y')
        GlobalDBHandler().add_historical_prices(entries=[HistoricalPrice(
            from_asset=from_asset,
            to_asset=to_asset,
            source=HistoricalPriceOracle.DEFILLAMA,
            timestamp=date_timestamp,
            price=price,
        )])
        return price

    def all_coins(self) -> Dict[str, Dict[str, Any]]:
        """no op for defillama. Required for the interface"""
        return {}
