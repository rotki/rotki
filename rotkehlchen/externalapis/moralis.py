import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final

import requests

from rotkehlchen.assets.asset import Asset, AssetWithOracles
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
from rotkehlchen.utils.misc import set_user_agent, ts_now
from rotkehlchen.utils.mixins.penalizable_oracle import PenalizablePriceOracleMixin
from rotkehlchen.utils.network import create_session

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MORALIS_BASE_URL: Final = 'https://deep-index.moralis.io/api/v2.2'
# Mapping of the chains rotki supports to the chain identifiers used by the Moralis
# token price API. Only chains supported by the Moralis price endpoint are included.
CHAIN_ID_TO_MORALIS_CHAIN: Final = {
    ChainID.ETHEREUM: 'eth',
    ChainID.OPTIMISM: 'optimism',
    ChainID.BINANCE_SC: 'bsc',
    ChainID.GNOSIS: 'gnosis',
    ChainID.POLYGON_POS: 'polygon',
    ChainID.BASE: 'base',
    ChainID.ARBITRUM_ONE: 'arbitrum',
    ChainID.AVALANCHE: 'avalanche',
}


class Moralis(
    ExternalServiceWithApiKeyOptionalDB,
    HistoricalPriceOracleInterface,
    PenalizablePriceOracleMixin,
):
    """Moralis price oracle. Queries USD prices for EVM tokens by contract address.

    Historical prices are keyed by block number, so a timestamp is first resolved to a
    block via the Moralis dateToBlock endpoint and then used to query the token price.
    """

    def __init__(self, database: 'DBHandler | None') -> None:
        ExternalServiceWithApiKeyOptionalDB.__init__(
            self,
            database=database,
            service_name=ExternalService.MORALIS,
        )
        HistoricalPriceOracleInterface.__init__(self, oracle_name='moralis')
        PenalizablePriceOracleMixin.__init__(self)
        self.session = create_session()
        set_user_agent(self.session)
        self.db: DBHandler | None  # type: ignore  # "solve" the self.db discrepancy

    @staticmethod
    def _get_moralis_chain(asset: AssetWithOracles) -> tuple['EvmToken', str]:
        """Resolve an asset to its EVM token and the Moralis chain identifier.

        May raise:
        - UnsupportedAsset if the asset is not an EVM token or its chain is not
        supported by the Moralis price API.
        """
        if asset.is_evm_token() is False:
            raise UnsupportedAsset(asset.identifier)

        token = asset.resolve_to_evm_token()
        if (chain := CHAIN_ID_TO_MORALIS_CHAIN.get(token.chain_id)) is None:
            raise UnsupportedAsset(asset.identifier)

        return token, chain

    def query_current_price(
            self,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
    ) -> Price:
        """
        Docs: https://docs.moralis.com/web3-data-api/evm/reference/price/get-token-price

        May raise:
        - RemoteError if there is a problem querying Moralis.
        """
        try:
            token, chain = self._get_moralis_chain(from_asset)
        except UnsupportedAsset:
            log.warning(
                'Tried to query current price using Moralis from %s to %s. But from_asset '
                'is not supported in moralis',
                from_asset.identifier,
                to_asset.identifier,
            )
            return ZERO_PRICE

        result = self._query(
            endpoint=f'erc20/{token.evm_address}/price',
            params={'chain': chain},
        )
        usd_price = self._deserialize_price(
            result=result,
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
        Docs: https://docs.moralis.com/web3-data-api/evm/reference/price/get-token-price

        May raise:
        - RemoteError if there is a problem querying Moralis
        - NoPriceForGivenTimestamp if no price could be found
        - PriceQueryUnsupportedAsset if either from_asset or to_asset are not supported
        """
        try:
            from_asset = from_asset.resolve_to_asset_with_oracles()
            to_asset = to_asset.resolve_to_asset_with_oracles()
        except UnknownAsset as e:
            raise PriceQueryUnsupportedAsset(e.identifier) from e

        try:
            token, chain = self._get_moralis_chain(from_asset)
        except UnsupportedAsset as e:
            log.warning(
                'Tried to query moralis historical price from %s to %s. But from_asset '
                'is not supported in moralis',
                from_asset.identifier,
                to_asset.identifier,
            )
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
            ) from e

        to_block = self._timestamp_to_block(chain=chain, timestamp=timestamp)
        result = self._query(
            endpoint=f'erc20/{token.evm_address}/price',
            params={'chain': chain, 'to_block': str(to_block)},
        )
        if (usd_price := self._deserialize_price(
            result=result,
            from_asset=from_asset,
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
            to_asset: Asset,  # pylint: disable=unused-argument
            timestamp: Timestamp,  # pylint: disable=unused-argument
            seconds: int | None = None,  # pylint: disable=unused-argument
    ) -> bool:
        return not self.is_penalized()

    def _timestamp_to_block(self, chain: str, timestamp: Timestamp) -> int:
        """Resolve a timestamp to the closest block number on the given chain via Moralis.

        Docs: https://docs.moralis.com/web3-data-api/evm/reference/get-date-to-block

        May raise:
        - RemoteError if there is a problem querying Moralis or the response is malformed.
        """
        result = self._query(
            endpoint='dateToBlock',
            params={'chain': chain, 'date': str(timestamp)},
        )
        try:
            return int(result['block'])
        except (KeyError, ValueError, TypeError) as e:
            error_msg = f'missing key {e!s}' if isinstance(e, KeyError) else str(e)
            raise RemoteError(
                f'Moralis dateToBlock response for {chain=} at {timestamp=} could not be '
                f'deserialized due to: {error_msg}',
            ) from e

    @staticmethod
    def _deserialize_price(
            result: dict[str, Any],
            from_asset: Asset,
            to_asset: Asset,
    ) -> Price:
        """Deserialize the USD price out of a Moralis token price response.

        If price data is missing or invalid, ZERO_PRICE is returned.
        """
        try:
            if (usd_price := result.get('usdPrice')) is None:
                log.warning(
                    'Queried Moralis price API from %s to %s, but received no usdPrice '
                    'in response',
                    from_asset.identifier,
                    to_asset.identifier,
                )
                return ZERO_PRICE

            return deserialize_price(str(usd_price))
        except DeserializationError as e:
            log.warning(
                'Queried Moralis price API from %s to %s. Failed to deserialize price '
                'data due to: %s',
                from_asset.identifier,
                to_asset.identifier,
                e,
            )
            return ZERO_PRICE

    def _query(
            self,
            endpoint: str,
            params: dict[str, str],
    ) -> dict[str, Any]:
        """
        May raise:
        - RemoteError
        """
        api_key = self._get_api_key()
        assert api_key is not None, "Can't be None since Moralis is added as an oracle only if there is an api key"  # noqa: E501
        url = f'{MORALIS_BASE_URL}/{endpoint}'
        log.debug('Querying moralis api: url=%s with params=%s', url, params)
        try:
            response = self.session.get(
                url=url,
                params=params,
                headers={'X-API-Key': api_key},
                timeout=CachedSettings().get_timeout_tuple(),
            )
        except requests.RequestException as e:
            self.penalty_info.note_failure_or_penalize()
            raise RemoteError(f'Moralis API request failed due to {e!s}') from e

        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            self.last_rate_limit = ts_now()
            msg = f'Got rate limited by Moralis API querying {url}'
            log.warning(msg)
            raise RemoteError(message=msg, error_code=HTTPStatus.TOO_MANY_REQUESTS)

        if response.status_code != HTTPStatus.OK:
            msg = (
                f'Moralis API request {response.url} failed with HTTP status '
                f'code: {response.status_code} with reason: {response.text}'
            )
            raise RemoteError(msg)

        try:
            decoded_json = response.json()
        except requests.RequestException as e:
            msg = f'Invalid JSON in Moralis API response. {e}'
            raise RemoteError(msg) from e

        return decoded_json
