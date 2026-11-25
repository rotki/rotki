import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final, Literal, NamedTuple

import requests

from rotkehlchen.constants import HOUR_IN_SECONDS
from rotkehlchen.constants.assets import A_AVAX, A_BSC_BNB, A_ETH, A_USD
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import RemoteError, cause_for_status
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKeyOptionalDB
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.interfaces import HistoricalPriceOracleInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ExternalService, Price, Timestamp, TokenKind
from rotkehlchen.utils.misc import iso8601ts_to_timestamp, set_user_agent, ts_now
from rotkehlchen.utils.mixins.penalizable_oracle import PenalizablePriceOracleMixin
from rotkehlchen.utils.network import create_session

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset, AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# The native coins of the chains Alchemy covers, which it prices by symbol. Every other asset
# that is not an EVM token is looked up by symbol too, but nothing says Alchemy knows it.
ALCHEMY_NATIVE_ASSETS: Final = frozenset({A_ETH, A_BSC_BNB, A_AVAX})


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
            (
                self.symbol is not None and
                entry.get('symbol') == self.symbol
            ) or
            (
                self.address is not None and
                self.network is not None and
                entry.get('network') == self.network and
                entry.get('address') == self.address
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

    def __init__(
            self,
            database: DBHandler | None,
            msg_aggregator: MessagesAggregator | None = None,
    ) -> None:
        ExternalServiceWithApiKeyOptionalDB.__init__(
            self,
            database=database,
            service_name=ExternalService.ALCHEMY,
        )
        HistoricalPriceOracleInterface.__init__(self, oracle_name='alchemy')
        PenalizablePriceOracleMixin.__init__(self, msg_aggregator=msg_aggregator)
        self.session = create_session(retry_policy='no_read_retries')
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
        usd_price, is_confirmed_no_data = self._deserialize_historical_price(
            result=result,
            alchemy_asset_data=alchemy_asset_data,
            from_asset=from_asset,
            timestamp=timestamp,
            to_asset=to_asset,
        )
        if usd_price == ZERO_PRICE:
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
                rate_limited=False,
                cacheable_miss=is_confirmed_no_data,
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

    def supports_history_of(
            self,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
            timestamp: Timestamp,
    ) -> bool:
        """Alchemy prices the tokens it covers on the EVM chains it supports, and the native
        coins of those chains, in USD.

        Other assets are looked up by symbol, which says nothing about whether Alchemy knows them,
        so of those only the native coins are claimed.
        """
        if from_asset.is_evm_token() is False:
            return from_asset in ALCHEMY_NATIVE_ASSETS
        self._get_alchemy_asset_data(from_asset)
        return self.covers_token(from_asset)

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
            if asset.token_kind == TokenKind.ERC721:  # the price api is per contract and can't price a collectible  # noqa: E501
                raise UnsupportedAsset(asset.identifier)

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
            result: Any,
            timestamp: Timestamp,
            alchemy_asset_data: AlchemyAssetData,
            from_asset: Asset,
            to_asset: Asset,
    ) -> tuple[Price, bool]:
        """Deserializes historical price data from Alchemy API response.

        Returns `(price, is_confirmed_no_data)`. `is_confirmed_no_data` is True only when
        the response matched the requested asset in USD and validly reported empty `data`
        or a zero price.
        """
        if not isinstance(result, dict):
            return ZERO_PRICE, False

        try:
            if not alchemy_asset_data.matches_api_response(result):
                log.warning(
                    f'Queried Alchemy API from {from_asset.identifier} to {to_asset.identifier}, '
                    f'but received mismatched symbol in response',
                )
                return ZERO_PRICE, False

            if result['currency'] != 'usd':
                log.warning(
                    f'Queried Alchemy API from {from_asset.identifier} to {to_asset.identifier}, '
                    f'but received non-USD currency in response',
                )
                return ZERO_PRICE, False

            if not isinstance(data := result.get('data'), list):
                log.warning(
                    'Queried Alchemy API from %s to %s, '
                    'but received invalid historical price data in response',
                    from_asset.identifier,
                    to_asset.identifier,
                )
                return ZERO_PRICE, False

            if len(data) == 0:
                log.warning(
                    f'Queried Alchemy API from {from_asset.identifier} to {to_asset.identifier}, '
                    f'but received no historical price data in response',
                )
                return ZERO_PRICE, True

            closest_price = min(
                data,
                key=lambda x: abs(timestamp - int(iso8601ts_to_timestamp(x['timestamp']))),
            )
            price = deserialize_price(closest_price['value'])
        except (DeserializationError, KeyError, TypeError, ValueError) as e:
            error_msg = f'missing key {e!s}' if isinstance(e, KeyError) else str(e)
            log.warning(
                f'Queried Alchemy Price API from {from_asset.identifier} to {to_asset.identifier}. '  # noqa: E501
                f'Failed to deserialize historical price data due to: {error_msg}',
            )
            return ZERO_PRICE, False
        else:
            return price, price == ZERO_PRICE

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
            self.note_request_failure(e)
            raise RemoteError(
                f'Alchemy API request failed due to {e!s}',
                cause=FailureCause.NETWORK,
            ) from e

        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            self.last_rate_limit = ts_now()
            msg = f'Got rate limited by Alchemy API querying {url}'
            log.warning(msg)
            raise RemoteError(
                message=msg, error_code=HTTPStatus.TOO_MANY_REQUESTS,
                cause=FailureCause.RATE_LIMITED,
            )

        if response.status_code != HTTPStatus.OK:
            msg = (
                f'Alchemy API request {response.url} failed with HTTP status '
                f'code: {response.status_code} with reason: {response.text}'
            )
            raise RemoteError(msg, cause=cause_for_status(response.status_code))

        try:
            decoded_json = response.json()
        except requests.RequestException as e:
            msg = f'Invalid JSON in Alchemy API response. {e}'
            raise RemoteError(msg, cause=FailureCause.BAD_DATA) from e

        return decoded_json
