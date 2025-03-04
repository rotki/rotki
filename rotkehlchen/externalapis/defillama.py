import json
import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import requests

from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKeyOptionalDB
from rotkehlchen.fval import FVal
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.interfaces import HistoricalPriceOracleInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ExternalService, Price, Timestamp
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.mixins.penalizable_oracle import PenalizablePriceOracleMixin
from rotkehlchen.utils.network import create_session

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
MIN_DEFILLAMA_CONFIDENCE = FVal('0.20')


class Defillama(
        ExternalServiceWithApiKeyOptionalDB,
        HistoricalPriceOracleInterface,
        PenalizablePriceOracleMixin,
):

    def __init__(self, database: 'DBHandler | None') -> None:
        ExternalServiceWithApiKeyOptionalDB.__init__(
            self,
            database=database,
            service_name=ExternalService.DEFILLAMA,
        )
        HistoricalPriceOracleInterface.__init__(self, oracle_name='defillama')
        PenalizablePriceOracleMixin.__init__(self)
        self.session = create_session()
        self.session.headers.update({'User-Agent': 'rotkehlchen'})
        self.db: DBHandler | None  # type: ignore  # "solve" the self.db discrepancy

    def _query(
            self,
            module: str,
            subpath: str | None = None,
            options: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Performs a defillama query

        May raise:
        - RemoteError if there is a problem querying defillama
        """
        if (api_key := self._get_api_key()) is not None:
            base_url = f'https://pro-api.llama.fi/{api_key}/coins/'
        else:
            base_url = 'https://coins.llama.fi/'

        if options is None:
            options = {}
        url = base_url + f'{module}/{subpath or ""}'
        log.debug(f'Querying defillama: {url=} with {options=}')
        try:
            response = self.session.get(
                url=url,
                params=options,
                timeout=CachedSettings().get_timeout_tuple(),
            )
        except requests.exceptions.RequestException as e:
            self.penalty_info.note_failure_or_penalize()
            raise RemoteError(f'Defillama API request failed due to {e!s}') from e

        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            self.last_rate_limit = ts_now()
            msg = f'Got rate limited by Defillama querying {url}'
            log.warning(msg)
            raise RemoteError(message=msg, error_code=HTTPStatus.TOO_MANY_REQUESTS)

        if response.status_code != 200:
            msg = (
                f'Defillama API request {response.url} failed with HTTP status '
                f'code: {response.status_code}'
            )
            raise RemoteError(msg)

        try:
            decoded_json = json.loads(response.text)
        except json.decoder.JSONDecodeError as e:
            msg = f'Invalid JSON in Defillama response. {e}'
            raise RemoteError(msg) from e

        return decoded_json

    def _get_asset_id(self, asset: AssetWithOracles) -> str:
        """
        Create the id to be used in Defillama.
        May raise:
        - UnsupportedAsset
        """
        if asset.is_evm_token() is True:
            asset = asset.resolve_to_evm_token()
            # The evm names for chains that we give don't match what defillama
            # uses in all the cases
            if asset.chain_id == ChainID.POLYGON_POS:
                chain_name = 'polygon'
            elif asset.chain_id == ChainID.ARBITRUM_ONE:
                chain_name = 'arbitrum'
            elif asset.chain_id == ChainID.BINANCE_SC:
                chain_name = 'bsc'
            elif asset.chain_id == ChainID.AVALANCHE:
                chain_name = 'avax'
            elif asset.chain_id == ChainID.ZKSYNC_ERA:
                chain_name = 'era'
            else:
                chain_name = str(asset.chain_id)

            return f'{chain_name}:{asset.evm_address}'

        return f'coingecko:{asset.to_coingecko()}'

    @staticmethod
    def _deserialize_prices(
            result: dict[str, Any],
            coin_id_mapping: dict[str, AssetWithOracles],
            from_assets: list[AssetWithOracles],
            to_asset: AssetWithOracles,
    ) -> dict[AssetWithOracles, Price]:
        """
        Reads the response from defillama and returns a dict mapping assets to usd prices.
        If a price is not available, couldn't be deserialized or the confidence
        is too low, the asset is skipped. Returns an empty dict if no prices were found.
        """
        if 'coins' not in result or len(coins_result := result['coins']) == 0:
            log.warning(
                f'Queried Defillama current price from {from_assets} '
                f'to {to_asset}. But coins is not available in the result {result}',
            )
            return {}

        prices: dict[AssetWithOracles, Price] = {}
        for coin_id, from_asset in coin_id_mapping.items():
            try:
                coin_result_raw = coins_result[coin_id]
                if (
                    'confidence' in coin_result_raw and
                    FVal(coin_result_raw['confidence']) < MIN_DEFILLAMA_CONFIDENCE
                ):
                    # Defillama provides a confidence value ranking how good their confidence in
                    # reported price is. When their confidence in the price is lower than 20%
                    # ignore it. Probably a spam token
                    continue
                prices[from_asset] = deserialize_price(coin_result_raw['price'])
            except (KeyError, DeserializationError) as e:
                error_msg = f'Missing key in defillama response: {e!s}.' if isinstance(e, KeyError) else str(e)  # noqa: E501
                log.warning(
                    f'Queried Defillama current price from {from_asset.identifier} '
                    f'to {to_asset.identifier}. But got key error for {error_msg} when '
                    f'processing the result.',
                )
                continue

        return prices

    def query_current_price(
            self,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
    ) -> Price:
        """Wrapper for query_multiple_current_price when only querying a single price.
        Returns the asset price from defillama or ZERO_PRICE if no price is found.
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
        """Queries simple prices for from_assets to to_asset in Defillama.
        Returns a dict mapping assets to prices found. Assets for which no price was found
        are not included in the dict.

        May raise:
        - RemoteError if there is a problem querying defillama.
        """
        coin_id_mapping: dict[str, AssetWithOracles] = {}
        for from_asset in from_assets:
            try:
                coin_id_mapping[self._get_asset_id(from_asset)] = from_asset
            except UnsupportedAsset:
                log.warning(
                    f'Tried to query current price using Defillama from {from_asset} to '
                    f'{to_asset} but {from_asset} is not an EVM token and is not '
                    f'supported by defillama',
                )
                continue

        if len(coin_id_mapping) == 0:
            return {}

        usd_prices = self._deserialize_prices(
            result=self._query(
                module='prices',
                subpath=f'current/{",".join(coin_id_mapping.keys())}',
            ),
            coin_id_mapping=coin_id_mapping,
            from_assets=from_assets,
            to_asset=to_asset,
        )

        # Prices from defillama are usd prices, so get rate from usd to to_asset
        rate_price = Inquirer.find_price(from_asset=A_USD, to_asset=to_asset) if to_asset != A_USD else ONE  # noqa: E501
        return {
            asset: Price(usd_price * rate_price)
            for asset, usd_price in usd_prices.items() if usd_price != ZERO_PRICE
        }

    def can_query_history(
            self,
            from_asset: Asset,  # pylint: disable=unused-argument
            to_asset: Asset,
            timestamp: Timestamp,
            seconds: int | None = None,
    ) -> bool:
        return not self.is_penalized()

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

        try:
            coin_id = self._get_asset_id(from_asset)
        except UnsupportedAsset as e:
            log.warning(
                f'Tried to query historical price using Defillama from {from_asset} to '
                f'{to_asset} at {timestamp} but {from_asset} is not an EVM token or is not '
                f'supported by coingecko',
            )
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
                rate_limited=False,
            ) from e

        result = self._query(
            module='prices',
            subpath=f'historical/{timestamp}/{coin_id}',
        )

        if (usd_price := self._deserialize_prices(
            result=result,
            coin_id_mapping={coin_id: from_asset},
            from_assets=[from_asset],
            to_asset=to_asset,
        ).get(from_asset, ZERO_PRICE)) == ZERO_PRICE:
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
                rate_limited=False,
            )

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

        return price
