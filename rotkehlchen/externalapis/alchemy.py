import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Literal, NamedTuple

import requests

from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.constants import HOUR_IN_SECONDS
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKeyOptionalDB
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.interfaces import HistoricalPriceOracleInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ExternalService, Price, Timestamp
from rotkehlchen.utils.misc import iso8601ts_to_timestamp, set_user_agent, ts_now
from rotkehlchen.utils.mixins.penalizable_oracle import PenalizablePriceOracleMixin
from rotkehlchen.utils.network import create_session

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AlchemyAssetData(NamedTuple):
    """Data structure for representing assets in Alchemy API requests.

    Can represent either a token by symbol (e.g. 'ETH') or a token
    by address on a specific network (e.g. address on Ethereum mainnet).
    """
    symbol: str | None = None
    address: str | None = None
    network: str | None = None

    def matches_api_response(
            self,
            entry: dict[str, Any],
    ) -> bool:
        """Check if the API response entry matches the asset identifier."""
        return (
            ('symbol' in entry and entry['symbol'] == self.symbol is not None) or
            (
                'address' in entry and
                entry['network'] == self.network and
                entry['address'] == self.address
            )
        )

    def serialize_for_current_price(self) -> dict[str, Any]:
        """Serialize the asset data for current price API request."""
        if self.symbol is not None:
            return {
                'verb': 'GET',
                'endpoint': 'by-symbol',
                'params': {'symbols': self.symbol},
            }

        return {
            'verb': 'POST',
            'endpoint': 'by-address',
            'payload': {'addresses': [{'address': self.address, 'network': self.network}]},
        }

    def serialize_for_historical_price(self, timestamp: Timestamp) -> dict[str, Any]:
        """Serialize the asset data for historical price API request."""
        result: dict[str, Any] = {
            'verb': 'POST',
            'endpoint': 'historical',
            'payload': {
                'interval': '1h',
                'endTime': timestamp + HOUR_IN_SECONDS,
                'startTime': timestamp - HOUR_IN_SECONDS,
            },
        }
        if self.symbol is not None:
            result['payload']['symbol'] = self.symbol
        else:
            result['payload']['network'] = self.network
            result['payload']['address'] = self.address

        return result


class Alchemy(
    ExternalServiceWithApiKeyOptionalDB,
    HistoricalPriceOracleInterface,
    PenalizablePriceOracleMixin,
):

    def __init__(self, database: 'DBHandler | None') -> None:
        ExternalServiceWithApiKeyOptionalDB.__init__(
            self,
            database=database,
            service_name=ExternalService.ALCHEMY,
        )
        HistoricalPriceOracleInterface.__init__(self, oracle_name='alchemy')
        PenalizablePriceOracleMixin.__init__(self)
        self.session = create_session()
        set_user_agent(self.session)
        self.db: DBHandler | None  # type: ignore  # "solve" the self.db discrepancy

    def query_current_price(
            self,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
    ) -> Price:
        """
        Docs:
            https://docs.alchemy.com/reference/get-token-prices-by-symbol
            https://docs.alchemy.com/reference/get-token-prices-by-address

        May raise:
        - RemoteError if there is a problem querying Alchemy.
        """
        try:
            alchemy_asset_data = self._get_alchemy_asset_data(from_asset)
        except UnsupportedAsset:
            log.warning(
                f'Tried to query current price using Alchemy from {from_asset.identifier} '
                f'to {to_asset.identifier}. But from_asset is not supported in alchemy',
            )
            return ZERO_PRICE

        result = self._query(**alchemy_asset_data.serialize_for_current_price())
        usd_price = self._deserialize_current_price(
            alchemy_asset_data=alchemy_asset_data,
            result=result['data'],
            from_asset=from_asset,
            to_asset=to_asset,
        )
        if usd_price == ZERO_PRICE or to_asset == A_USD:
            return usd_price

        # The price is in USD, but we need to convert it to the target currency.
        rate_price = Inquirer.find_price(from_asset=A_USD, to_asset=to_asset)
        return Price(usd_price * rate_price)

    def query_historical_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        """
        Docs: https://docs.alchemy.com/reference/get-historical-token-prices

        May raise:
        - RemoteError if there is a problem querying Alchemy
        - NoPriceForGivenTimestamp if no price could be found
        - PriceQueryUnsupportedAsset if either from_asset or to_asset are not supported
        """
        try:
            from_asset = from_asset.resolve_to_asset_with_oracles()
            to_asset = to_asset.resolve_to_asset_with_oracles()
        except UnknownAsset as e:
            raise PriceQueryUnsupportedAsset(e.identifier) from e

        try:
            alchemy_asset_data = self._get_alchemy_asset_data(from_asset)
        except UnsupportedAsset as e:
            log.warning(
                f'Tried to query alchemy historical price from {from_asset.identifier} '
                f'to {to_asset.identifier}. But from_asset is not supported in alchemy',
            )
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
            ) from e

        result = self._query(**alchemy_asset_data.serialize_for_historical_price(timestamp))
        if (usd_price := self._deserialize_historical_price(
            result=result,
            alchemy_asset_data=alchemy_asset_data,
            from_asset=from_asset,
            timestamp=timestamp,
            to_asset=to_asset,
        )) == ZERO_PRICE:
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
                rate_limited=False,
            )

        if to_asset != A_USD:  # we need to query intermediate price in this case.
            to_asset_price = PriceHistorian().query_historical_price(
                from_asset=A_USD,
                to_asset=to_asset,
                timestamp=timestamp,
            )
            price = Price(usd_price * to_asset_price)
        else:
            price = usd_price

        return price

    def can_query_history(
            self,
            from_asset: Asset,  # pylint: disable=unused-argument
            to_asset: Asset,
            timestamp: Timestamp,
            seconds: int | None = None,
    ) -> bool:
        return not self.is_penalized()

    @staticmethod
    def _get_alchemy_asset_data(asset: AssetWithOracles) -> AlchemyAssetData:
        """
        May raise:
        - UnsupportedAsset
        """
        if asset.is_evm_token() is True:
            asset = asset.resolve_to_evm_token()
            if asset.chain_id == ChainID.POLYGON_POS:
                network = 'polygon-mainnet'
            elif asset.chain_id == ChainID.ARBITRUM_ONE:
                network = 'arb-mainnet'
            elif asset.chain_id == ChainID.BINANCE_SC:
                network = 'bnb-mainnet'
            elif asset.chain_id == ChainID.AVALANCHE:
                network = 'avax-mainnet'
            elif asset.chain_id == ChainID.ZKSYNC_ERA:
                network = 'zksync-mainnet'
            elif asset.chain_id == ChainID.ETHEREUM:
                network = 'eth-mainnet'
            elif asset.chain_id == ChainID.POLYGON_ZKEVM:
                network = 'polygonzkevm-mainnet'
            elif asset.chain_id == ChainID.SCROLL:
                network = 'scroll-mainnet'
            elif asset.chain_id == ChainID.GNOSIS:
                network = 'gnosis-mainnet'
            elif asset.chain_id == ChainID.BASE:
                network = 'base-mainnet'
            elif asset.chain_id == ChainID.FANTOM:
                network = 'fantom-mainnet'
            elif asset.chain_id == ChainID.ARBITRUM_NOVA:
                network = 'arbnova-mainnet'
            else:
                raise UnsupportedAsset(asset.identifier)

            return AlchemyAssetData(
                network=network,
                address=asset.evm_address,
            )

        return AlchemyAssetData(symbol=asset.symbol)

    @staticmethod
    def _deserialize_current_price(
            result: list[dict[str, Any]],
            alchemy_asset_data: AlchemyAssetData,
            from_asset: Asset,
            to_asset: Asset,
    ) -> Price:
        """Deserializes current price data from Alchemy API response.

        If price data is missing, invalid, or there's an error, ZERO_PRICE is returned.
        Otherwise, the deserialized price is returned.
        """
        usd_price = ZERO_PRICE
        try:
            for entry in result:
                if not alchemy_asset_data.matches_api_response(entry):
                    continue

                if 'error' in entry:
                    log.warning(
                        f'Queried Alchemy Price API from {from_asset.identifier} to {to_asset.identifier}. '  # noqa: E501
                        f'API returned error: {entry["error"]}',
                    )
                    return usd_price

                if len(prices := entry['prices']) == 0:
                    log.warning(
                        f'Queried Alchemy Price API from {from_asset.identifier} to {to_asset.identifier}, '  # noqa: E501
                        f'but received no prices in response',
                    )
                    return usd_price

                for price in prices:
                    if price['currency'] == 'usd':
                        usd_price = deserialize_price(price['value'])
                        break

                else:  # usd price not found
                    log.error(
                        f'Queried Alchemy Price API from {from_asset.identifier} to '
                        f'{to_asset.identifier}, but received non-USD price response',
                    )

        except (DeserializationError, KeyError) as e:
            error_msg = f'missing key {e!s}' if isinstance(e, KeyError) else str(e)
            log.warning(
                f'Queried Alchemy Price API from {from_asset.identifier} to {to_asset.identifier}. '  # noqa: E501
                f'Failed to deserialize price data due to: {error_msg}',
            )

        return usd_price

    @staticmethod
    def _deserialize_historical_price(
            result: dict[str, Any],
            timestamp: Timestamp,
            alchemy_asset_data: AlchemyAssetData,
            from_asset: Asset,
            to_asset: Asset,
    ) -> Price:
        """Deserializes historical price data from Alchemy API response.

        If price data is missing, invalid, or there's an error, ZERO_PRICE is returned.
        Otherwise, the deserialized price is returned.
        """
        try:
            if not alchemy_asset_data.matches_api_response(result):
                log.warning(
                    f'Queried Alchemy API from {from_asset.identifier} to {to_asset.identifier}, '
                    f'but received mismatched symbol in response',
                )
                return ZERO_PRICE

            if result['currency'] != 'usd':
                log.warning(
                    f'Queried Alchemy API from {from_asset.identifier} to {to_asset.identifier}, '
                    f'but received non-USD currency in response',
                )
                return ZERO_PRICE

            if not (data := result.get('data', [])):
                log.warning(
                    f'Queried Alchemy API from {from_asset.identifier} to {to_asset.identifier}, '
                    f'but received no historical price data in response',
                )
                return ZERO_PRICE

            closest_price = min(
                data,
                key=lambda x: abs(timestamp - int(iso8601ts_to_timestamp(x['timestamp']))),
            )
            return deserialize_price(closest_price['value'])

        except (DeserializationError, KeyError, ValueError) as e:
            error_msg = f'missing key {e!s}' if isinstance(e, KeyError) else str(e)
            log.warning(
                f'Queried Alchemy Price API from {from_asset.identifier} to {to_asset.identifier}. '  # noqa: E501
                f'Failed to deserialize historical price data due to: {error_msg}',
            )
            return ZERO_PRICE

    def _query(
            self,
            verb: Literal['GET', 'POST'],
            endpoint: Literal['by-symbol', 'by-address', 'historical'],
            params: dict[str, str] | None = None,
            payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        May raise:
        - RemoteError
        """
        api_key = self._get_api_key()
        assert api_key is not None, "Can't be None since Alchemy is added as an oracle only if there is an api key"  # noqa: E501
        url = f'https://api.g.alchemy.com/prices/v1/{api_key}/tokens/{endpoint}'
        log.debug(f'Querying alchemy api: {url=} with {payload=} and {params=}')
        try:
            response = self.session.request(
                method=verb,
                url=url,
                params=params,
                json=payload,
                timeout=CachedSettings().get_timeout_tuple(),
            )
        except requests.RequestException as e:
            self.penalty_info.note_failure_or_penalize()
            raise RemoteError(f'Alchemy API request failed due to {e!s}') from e

        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            self.last_rate_limit = ts_now()
            msg = f'Got rate limited by Alchemy API querying {url}'
            log.warning(msg)
            raise RemoteError(message=msg, error_code=HTTPStatus.TOO_MANY_REQUESTS)

        if response.status_code != HTTPStatus.OK:
            msg = (
                f'Alchemy API request {response.url} failed with HTTP status '
                f'code: {response.status_code} with reason: {response.text}'
            )
            raise RemoteError(msg)

        try:
            decoded_json = response.json()
        except requests.RequestException as e:
            msg = f'Invalid JSON in Alchemy API response. {e}'
            raise RemoteError(msg) from e

        return decoded_json
