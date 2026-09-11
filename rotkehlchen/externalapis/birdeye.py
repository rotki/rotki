import logging
import time
from collections import defaultdict
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final

import requests

from rotkehlchen.concurrency import cancellable_sleep
from rotkehlchen.constants import ONE
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
from rotkehlchen.utils.misc import get_chunks, set_user_agent, ts_now
from rotkehlchen.utils.mixins.penalizable_oracle import PenalizablePriceOracleMixin
from rotkehlchen.utils.network import create_session
from rotkehlchen.utils.rate_limiter import TokenBucket

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset, AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

BIRDEYE_BASE_URL: Final = 'https://public-api.birdeye.so/defi'
BIRDEYE_SOLANA_CHAIN: Final = 'solana'
# Mapping of the EVM chains rotki supports to the `x-chain` header values Birdeye uses.
# Only chains Birdeye lists on its supported networks page are included.
CHAIN_ID_TO_BIRDEYE_CHAIN: Final = {
    ChainID.ETHEREUM: 'ethereum',
    ChainID.BINANCE_SC: 'bsc',
    ChainID.BASE: 'base',
    ChainID.ARBITRUM_ONE: 'arbitrum',
    ChainID.OPTIMISM: 'optimism',
    ChainID.POLYGON_POS: 'polygon',
    ChainID.AVALANCHE: 'avalanche',
    ChainID.ZKSYNC_ERA: 'zksync',
    ChainID.HYPERLIQUID: 'hyperevm',
}
# multi_price accepts at most 100 addresses per request
BIRDEYE_MULTI_PRICE_CHUNK_SIZE: Final = 100
# The free Standard package is documented as 1 request per second, but a request made at
# second N only frees the slot at N + 2 (X-RateLimit-Reset), denied requests count too and
# a 429 comes with Retry-After: 1. So on the free tier requests are spaced 2 seconds apart
# with no burst, and a 429 that slips through anyway is retried after the wait the
# response asks for. Every paid package allows at least 15 rps. There is no tier probe
# endpoint, but multi_price is paid-only, so a successful batched call is the signal
# that the key is on a paid package.
BIRDEYE_STANDARD_RATE_LIMIT_RPS: Final = 0.5
BIRDEYE_STANDARD_RATE_LIMIT_BURST: Final = 1
BIRDEYE_RATE_LIMIT_RETRIES: Final = 2
BIRDEYE_RATE_LIMIT_MIN_WAIT: Final = 1.0
BIRDEYE_RATE_LIMIT_MAX_WAIT: Final = 5.0
# margin on top of the reset timestamp: our clock and Birdeye's are not the same clock
BIRDEYE_RATE_LIMIT_RESET_MARGIN: Final = 0.2
BIRDEYE_PAID_RATE_LIMIT_RPS: Final = 15.0
BIRDEYE_PAID_RATE_LIMIT_BURST: Final = 15
# history_price returns a series of (unixTime, value) points for a window. The exact
# timestamp endpoint is Solana-only and paid-only, so a narrow hourly window around
# the requested timestamp is queried first and a wider daily one only if it is empty.
# Each attempt costs the same compute units regardless of the window size.
BIRDEYE_HISTORY_WINDOWS: Final = (
    ('1H', 6 * 3600),
    ('1D', 2 * 24 * 3600),
)
# Status codes Birdeye answers with when the key's package does not include an
# endpoint. Seeing one on the batched endpoint means singles must be used instead.
BIRDEYE_PACKAGE_DENIED_STATUSES: Final = (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN)


class Birdeye(
        ExternalServiceWithApiKeyOptionalDB,
        HistoricalPriceOracleInterface,
        PenalizablePriceOracleMixin,
):
    """Birdeye price oracle. Queries USD prices for Solana and EVM tokens by address.

    Docs: https://data.birdeye.so/docs/data-api/price-ohlcv
    """

    def __init__(self, database: DBHandler | None) -> None:
        ExternalServiceWithApiKeyOptionalDB.__init__(
            self,
            database=database,
            service_name=ExternalService.BIRDEYE,
        )
        HistoricalPriceOracleInterface.__init__(self, oracle_name='birdeye')
        PenalizablePriceOracleMixin.__init__(self)
        self.session = create_session()
        set_user_agent(self.session)
        self.db: DBHandler | None  # type: ignore  # "solve" the self.db discrepancy
        self._rate_limiter = TokenBucket(
            rps=BIRDEYE_STANDARD_RATE_LIMIT_RPS,
            capacity=BIRDEYE_STANDARD_RATE_LIMIT_BURST,
        )
        # None until the first batched call decides it. Batching is paid-only, so a
        # denial flips this to False for the rest of the session and a success to True.
        self._batching_supported: bool | None = None

    def on_api_key_changed(self) -> None:
        """A new key may be on a different package, so forget what the old one taught us"""
        self._rate_limiter.reset(
            rps=BIRDEYE_STANDARD_RATE_LIMIT_RPS,
            capacity=BIRDEYE_STANDARD_RATE_LIMIT_BURST,
        )
        self._batching_supported = None

    @staticmethod
    def _get_chain_and_address(asset: AssetWithOracles) -> tuple[str, str]:
        """Resolve an asset to the Birdeye chain name and the token address on it.

        May raise:
        - UnsupportedAsset if the asset is neither a Solana token nor an EVM token on a
        chain Birdeye supports.
        """
        if asset.is_solana_token():
            return BIRDEYE_SOLANA_CHAIN, asset.resolve_to_solana_token().mint_address

        if asset.is_evm_token():
            token = asset.resolve_to_evm_token()
            if (chain := CHAIN_ID_TO_BIRDEYE_CHAIN.get(token.chain_id)) is not None:
                return chain, token.evm_address

        raise UnsupportedAsset(asset.identifier)

    def _query(
            self,
            endpoint: str,
            chain: str,
            params: dict[str, str],
    ) -> dict[str, Any]:
        """Query a Birdeye endpoint and return its `data` payload.

        May raise:
        - RemoteError if the request fails, is rate limited, denied, or malformed. The
        HTTP status is set as the error code so callers can tell these cases apart.
        """
        api_key = self._get_api_key()
        assert api_key is not None, "Can't be None since Birdeye is added as an oracle only if there is an api key"  # noqa: E501
        url = f'{BIRDEYE_BASE_URL}/{endpoint}'
        log.debug('Querying birdeye: url=%s chain=%s with params=%s', url, chain, params)
        retries_left = BIRDEYE_RATE_LIMIT_RETRIES
        while True:
            self._rate_limiter.acquire()
            try:
                response = self.session.get(
                    url=url,
                    params=params,
                    headers={'X-API-KEY': api_key, 'x-chain': chain},
                    timeout=CachedSettings().get_timeout_tuple(),
                )
            except requests.RequestException as e:
                self.penalty_info.note_failure_or_penalize()
                raise RemoteError(f'Birdeye API request failed due to {e!s}') from e

            if response.status_code != HTTPStatus.TOO_MANY_REQUESTS:
                break

            self.last_rate_limit = ts_now()
            self._rate_limiter.shrink_after_429()
            wait = self._rate_limit_wait(response)
            if retries_left == 0 or wait > BIRDEYE_RATE_LIMIT_MAX_WAIT:
                msg = f'Got rate limited by Birdeye querying {url}'
                log.warning(msg)
                raise RemoteError(message=msg, error_code=HTTPStatus.TOO_MANY_REQUESTS)

            retries_left -= 1
            log.debug('Birdeye rate limited querying %s. Retrying in %.1f seconds', url, wait)
            cancellable_sleep(wait)

        if response.status_code != HTTPStatus.OK:
            raise RemoteError(
                message=(
                    f'Birdeye API request {response.url} failed with HTTP status '
                    f'code: {response.status_code} with reason: {response.text}'
                ),
                error_code=response.status_code,
            )

        try:
            decoded_json = response.json()
        except requests.RequestException as e:
            raise RemoteError(f'Invalid JSON in Birdeye API response. {e}') from e

        if (
            not isinstance(decoded_json, dict) or
            decoded_json.get('success') is not True or
            not isinstance(data := decoded_json.get('data'), dict)
        ):
            raise RemoteError(
                f'Birdeye API request {response.url} returned an unexpected response: '
                f'{response.text}',
            )

        return data

    @staticmethod
    def _rate_limit_wait(response: requests.Response) -> float:
        """Seconds to wait before retrying a request Birdeye answered with 429.

        Takes the longer of the Retry-After header and the distance to the
        X-RateLimit-Reset timestamp, and never less than the minimum wait.
        """
        wait = BIRDEYE_RATE_LIMIT_MIN_WAIT
        try:
            wait = max(wait, float(response.headers.get('Retry-After', 0)))
            if (reset := response.headers.get('X-RateLimit-Reset')) is not None:
                wait = max(wait, float(reset) - time.time() + BIRDEYE_RATE_LIMIT_RESET_MARGIN)
        except ValueError as e:
            log.debug('Ignoring unparsable Birdeye rate limit headers due to %s', e)

        return wait

    @staticmethod
    def _deserialize_price_entry(entry: Any, identifier: str) -> Price:
        """Read the `value` of a single Birdeye price entry.

        Birdeye omits the entry or returns null for a token it has not indexed, and
        ZERO_PRICE is returned for those and for any malformed value. The identifier
        names the token in the logs.
        """
        if not isinstance(entry, dict) or (value := entry.get('value')) is None:
            log.debug('Birdeye has no price for %s. Entry: %s', identifier, entry)
            return ZERO_PRICE

        try:
            return deserialize_price(str(value))
        except DeserializationError as e:
            log.warning(
                'Failed to deserialize Birdeye price %s for %s due to %s',
                value,
                identifier,
                e,
            )
            return ZERO_PRICE

    def _query_single_prices(
            self,
            chain: str,
            address_mapping: dict[str, AssetWithOracles],
    ) -> dict[AssetWithOracles, Price]:
        """Query the current USD price of each token one request at a time"""
        prices: dict[AssetWithOracles, Price] = {}
        for address, asset in address_mapping.items():
            try:
                data = self._query(endpoint='price', chain=chain, params={'address': address})
            except RemoteError as e:
                if e.error_code == HTTPStatus.TOO_MANY_REQUESTS:
                    raise
                log.debug(
                    'Birdeye failed to query price of %s: %s. Skipping.',
                    asset.identifier,
                    e,
                )
                continue

            if (price := self._deserialize_price_entry(
                entry=data,
                identifier=asset.identifier,
            )) != ZERO_PRICE:
                prices[asset] = price

        return prices

    def _query_batched_prices(
            self,
            chain: str,
            address_mapping: dict[str, AssetWithOracles],
    ) -> dict[AssetWithOracles, Price]:
        """Query the current USD prices of the given tokens with multi_price.

        multi_price is only included in the paid packages. The first denial marks batching
        as unsupported so the rest of the session goes straight to single lookups, and the
        first success marks it as supported and lifts the rate limit to the paid tier.

        May raise:
        - RemoteError if the package does not include multi_price or the query failed.
        """
        prices: dict[AssetWithOracles, Price] = {}
        lowercased_mapping = {address.lower(): asset for address, asset in address_mapping.items()}
        for chunk in get_chunks(list(address_mapping), BIRDEYE_MULTI_PRICE_CHUNK_SIZE):
            try:
                data = self._query(
                    endpoint='multi_price',
                    chain=chain,
                    params={'list_address': ','.join(chunk)},
                )
            except RemoteError as e:
                if e.error_code in BIRDEYE_PACKAGE_DENIED_STATUSES:
                    log.info('Birdeye multi_price is not included in the package of the configured key (%s). Using single price queries.', e)  # noqa: E501
                    self._batching_supported = False
                raise

            if self._batching_supported is None:
                self._batching_supported = True
                self._rate_limiter.widen(
                    observed_rps=BIRDEYE_PAID_RATE_LIMIT_RPS,
                    observed_capacity=BIRDEYE_PAID_RATE_LIMIT_BURST,
                )

            for address, entry in data.items():
                if (asset := lowercased_mapping.get(address.lower())) is None:
                    continue
                if (price := self._deserialize_price_entry(entry=entry, identifier=asset.identifier)) != ZERO_PRICE:  # noqa: E501
                    prices[asset] = price

        return prices

    def query_current_price(
            self,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
    ) -> Price:
        """Wrapper for query_multiple_current_prices when only querying a single price.
        Returns the asset price from Birdeye or ZERO_PRICE if no price is found.
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
        """Query current prices for from_assets to to_asset in Birdeye.

        Tokens are grouped per chain since the chain is a request header. Each group is
        queried batched when the package allows it and one token at a time otherwise.
        Returns a dict mapping assets to prices found. Assets for which no price was found
        are not included in the dict.

        May raise:
        - RemoteError if Birdeye rate limits us.
        """
        per_chain: defaultdict[str, dict[str, AssetWithOracles]] = defaultdict(dict)
        for from_asset in from_assets:
            try:
                chain, address = self._get_chain_and_address(from_asset)
            except UnsupportedAsset:
                log.debug('Tried to query current price using Birdeye from %s to %s but %s is not supported by Birdeye', from_asset, to_asset, from_asset)  # noqa: E501
                continue
            per_chain[chain][address] = from_asset

        if len(per_chain) == 0:
            return {}

        all_usd_prices: dict[AssetWithOracles, Price] = {}
        for chain, address_mapping in per_chain.items():
            if self._batching_supported is not False:
                try:
                    all_usd_prices.update(self._query_batched_prices(
                        chain=chain,
                        address_mapping=address_mapping,
                    ))
                    continue
                except RemoteError as e:
                    if e.error_code == HTTPStatus.TOO_MANY_REQUESTS:
                        raise
                    log.debug('Birdeye batched price query for %s failed: %s. Falling back to single queries.', chain, e)  # noqa: E501

            all_usd_prices.update(self._query_single_prices(
                chain=chain,
                address_mapping=address_mapping,
            ))

        if len(all_usd_prices) == 0:
            return {}

        # Prices from Birdeye are USD prices, so get the rate from USD to to_asset
        rate_price = Inquirer.find_price(from_asset=A_USD, to_asset=to_asset) if to_asset != A_USD else ONE  # noqa: E501
        return {asset: Price(usd_price * rate_price) for asset, usd_price in all_usd_prices.items()}  # noqa: E501

    def can_query_history(
            self,
            from_asset: Asset,  # pylint: disable=unused-argument
            to_asset: Asset,  # pylint: disable=unused-argument
            timestamp: Timestamp,  # pylint: disable=unused-argument
            seconds: int | None = None,  # pylint: disable=unused-argument
    ) -> bool:
        return not self.is_penalized()

    def _query_nearest_historical_usd_price(
            self,
            chain: str,
            address: str,
            timestamp: Timestamp,
    ) -> Price:
        """Query the price series around the timestamp and pick the point closest to it.

        Returns ZERO_PRICE if no window contains any point.

        May raise:
        - RemoteError if there is a problem querying Birdeye
        """
        for interval, half_window in BIRDEYE_HISTORY_WINDOWS:
            data = self._query(
                endpoint='history_price',
                chain=chain,
                params={
                    'address': address,
                    'address_type': 'token',
                    'type': interval,
                    'time_from': str(max(timestamp - half_window, 0)),
                    'time_to': str(timestamp + half_window),
                },
            )
            nearest_entry, nearest_distance = None, half_window + 1
            for entry in data.get('items', []):
                try:
                    distance = abs(int(entry['unixTime']) - timestamp)
                except (KeyError, TypeError, ValueError) as e:
                    log.warning('Skipping malformed Birdeye history entry %s due to %s', entry, e)
                    continue

                if distance < nearest_distance:
                    nearest_entry, nearest_distance = entry, distance

            if nearest_entry is not None:
                return self._deserialize_price_entry(
                    entry=nearest_entry,
                    identifier=f'{chain}:{address}',
                )

        return ZERO_PRICE

    def query_historical_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        """
        Docs: https://data.birdeye.so/docs/data-api/price-ohlcv/get-defi-history-price

        May raise:
        - RemoteError if there is a problem querying Birdeye
        - NoPriceForGivenTimestamp if no price could be found
        - PriceQueryUnsupportedAsset if either from_asset or to_asset are not supported
        """
        try:
            from_asset = from_asset.resolve_to_asset_with_oracles()
            to_asset = to_asset.resolve_to_asset_with_oracles()
        except UnknownAsset as e:
            raise PriceQueryUnsupportedAsset(e.identifier) from e

        try:
            chain, address = self._get_chain_and_address(from_asset)
        except UnsupportedAsset as e:
            log.debug('Tried to query historical price using Birdeye from %s to %s at %s but %s is not supported by Birdeye', from_asset, to_asset, timestamp, from_asset)  # noqa: E501
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
                rate_limited=False,
            ) from e

        if (usd_price := self._query_nearest_historical_usd_price(
            chain=chain,
            address=address,
            timestamp=timestamp,
        )) == ZERO_PRICE:
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
                rate_limited=False,
            )

        if to_asset == A_USD:
            return usd_price

        # We need to query the intermediate price in this case. Let the error propagate if
        # any happens in this subcall
        return Price(usd_price * PriceHistorian().query_historical_price(
            from_asset=A_USD,
            to_asset=to_asset,
            timestamp=timestamp,
        ))
