import logging
import threading
import time
from http import HTTPStatus
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal

import requests

from rotkehlchen.concurrency import cancellable_sleep
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import RemoteError, cause_for_status
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval_force_positive
from rotkehlchen.types import ExternalService, SupportedBlockchain, Timestamp
from rotkehlchen.utils.misc import set_user_agent, ts_now
from rotkehlchen.utils.network import create_session
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.fval import FVal
    from rotkehlchen.types import ApiKey, BTCAddress
    from rotkehlchen.utils.rate_limiter import TokenBucket

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

SOCHAIN_BASE_URL: Final = 'https://sochain.com/api/v3'
# A 429 says in Retry-After how many seconds to wait. For SoChain that is a second when
# too many requests run at the same time, but once the daily allowance of requests
# without an API key is used up it is the time left until the allowance resets at
# 00:00 UTC. So only short waits are waited out. A longer one fails the query, and the
# API is not asked again until that time has passed.
MAX_RETRY_AFTER: Final = 5
RATE_LIMIT_RETRIES: Final = 3
# After a short 429 slowed the requests down, their rate doubles again for every minute
# without another one, up to the rate the API was created with.
RATE_RECOVERY_SECONDS: Final = 60


def _retry_after_seconds(response: requests.Response) -> int:
    """Seconds to wait before retrying a request answered with 429.
    One second if the Retry-After header is missing or not a number of seconds."""
    try:
        return max(1, int(response.headers.get('Retry-After', 1)))
    except ValueError:
        return 1


class SoChainLikeApi:
    """Base of the APIs that answer like SoChain's v3 API. Every answer is
    {"status": "success", "data": ...} or {"status": "fail", "data": {"error_message": ...}},
    and a 429 says in Retry-After how many seconds to wait. None of them requires an API key.

    If a rate limiter is given, every request waits for it first. A short 429 halves its
    rate, which recovers over the following minutes (RATE_RECOVERY_SECONDS).
    """

    def __init__(self, name: str, rate_limiter: TokenBucket | None = None) -> None:
        self.name = name
        self.rate_limiter = rate_limiter
        self.configured_rps = rate_limiter.rps if rate_limiter is not None else None
        self.last_slowdown = 0.0
        # monotonic time until which the API asked not to be queried (a long Retry-After)
        self.unavailable_until = 0.0
        self.session = create_session()
        set_user_agent(self.session)

    def _recover_rate(self) -> None:
        """Double the rate limiter's rate, up to the configured one, if the last short 429
        was at least RATE_RECOVERY_SECONDS ago."""
        if (
            self.rate_limiter is None or
            self.configured_rps is None or
            self.rate_limiter.rps >= self.configured_rps or
            (now := time.monotonic()) - self.last_slowdown < RATE_RECOVERY_SECONDS
        ):
            return

        self.rate_limiter.widen(observed_rps=min(self.configured_rps, self.rate_limiter.rps * 2))
        self.last_slowdown = now

    def _query(self, url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
        """Query the given url, with the given headers, and return the data of the response.

        May raise:
        - RemoteError if the request fails, stays rate limited, or the API does not
        answer with success. The HTTP status is set as the error code.
        """
        if (wait := self.unavailable_until - time.monotonic()) > 0:
            raise RemoteError(
                message=(
                    f'{self.name} API request {url} was not sent. {self.name} asked not to '
                    f'be queried for another {int(wait) + 1} seconds'
                ),
                error_code=HTTPStatus.TOO_MANY_REQUESTS,
                cause=FailureCause.RATE_LIMITED,
            )

        retries_left = RATE_LIMIT_RETRIES
        while True:
            if self.rate_limiter is not None:
                self.rate_limiter.acquire()

            log.debug('Querying %s: %s', self.name, url)
            try:
                response = self.session.get(
                    url=url,
                    headers=headers,
                    timeout=CachedSettings().get_timeout_tuple(),
                )
            except requests.exceptions.RequestException as e:
                raise RemoteError(
                    f'{self.name} API request {url} failed due to {e!s}',
                    cause=FailureCause.NETWORK,
                ) from e

            if response.status_code != HTTPStatus.TOO_MANY_REQUESTS:
                self._recover_rate()
                break

            if (retry_after := _retry_after_seconds(response)) > MAX_RETRY_AFTER:
                # an allowance used up, not requests sent too fast: wait it out without
                # slowing the requests down
                self.unavailable_until = time.monotonic() + retry_after
            elif self.rate_limiter is not None:
                self.rate_limiter.shrink_after_429()
                self.last_slowdown = time.monotonic()

            if retry_after > MAX_RETRY_AFTER or retries_left == 0:
                raise RemoteError(
                    message=(
                        f'{self.name} API request {url} was rate limited. {self.name} '
                        f'asked to retry after {retry_after} seconds'
                    ),
                    error_code=HTTPStatus.TOO_MANY_REQUESTS,
                    cause=FailureCause.RATE_LIMITED,
                )

            retries_left -= 1
            log.debug('%s rate limited %s. Retrying in %s seconds', self.name, url, retry_after)
            cancellable_sleep(retry_after)

        try:
            result = jsonloads_dict(response.text)
        except JSONDecodeError as e:
            raise RemoteError(
                message=f'{self.name} API request {url} returned invalid JSON: {response.text}',
                error_code=response.status_code,
                cause=FailureCause.BAD_DATA,
            ) from e

        data = result.get('data')
        if (
            response.status_code != HTTPStatus.OK or
            result.get('status') != 'success' or
            not isinstance(data, dict)
        ):
            # a failure is explained in data.error_message
            reason = data.get('error_message') if isinstance(data, dict) else None
            raise RemoteError(
                message=(
                    f'{self.name} API request {url} failed with HTTP status code '
                    f'{response.status_code}: {reason or response.text}'
                ),
                error_code=response.status_code,
                cause=cause_for_status(response.status_code),
            )

        return data

    def _deserialize_balance(self, value: Any, address: BTCAddress) -> FVal:
        """Read a balance given as a decimal string of whole coins.

        May raise:
        - RemoteError if the value is not a number.
        """
        try:
            return deserialize_fval_force_positive(
                value=value,
                name='confirmed balance',
                location=f'{self.name} balance query',
            )
        except DeserializationError as e:
            raise RemoteError(
                f'Unexpected {self.name} balance {value} for {address}: {e!s}',
                cause=FailureCause.BAD_DATA,
            ) from e


class SoChain(SoChainLikeApi, ExternalServiceWithApiKey):
    """Client of the SoChain v3 API. An API key is optional and only raises the limits.

    Docs: https://sochain.com/docs
    """

    def __init__(self, network: Literal['DOGE'], database: DBHandler) -> None:
        SoChainLikeApi.__init__(self, name='SoChain')
        ExternalServiceWithApiKey.__init__(
            self,
            database=database,
            service_name=ExternalService.SOCHAIN,
        )
        self.network = network
        self.refused_key_lock = threading.Lock()
        self.reported_key_as_not_usable = False

    def on_api_key_changed(self) -> None:
        """Forget the cached key and what SoChain said about the previous one, so that the
        new key is used and SoChain is asked again right away."""
        self.api_key = None
        self.last_ts = Timestamp(0)
        self.unavailable_until = 0.0
        self.reported_key_as_not_usable = False

    def _handle_refused_key(self, api_key: ApiKey) -> None:
        """Find out why SoChain answered a request made with the given key with a 401, which
        has the same message for a key that does not work and for an account past its
        allowance. In the second case account_info still accepts the key.

        An account past its allowance is not asked again until the allowance resets at
        00:00 UTC. A key that does not work is reported to the user once.
        """
        with self.refused_key_lock:
            if (
                self.reported_key_as_not_usable or
                self.unavailable_until > time.monotonic() or
                api_key != self._get_api_key()  # changed while the request was in flight
            ):
                return

            try:
                status_code = self.session.get(
                    url=f'{SOCHAIN_BASE_URL}/account_info',
                    headers={'API-KEY': api_key},
                    timeout=CachedSettings().get_timeout_tuple(),
                ).status_code
            except requests.exceptions.RequestException as e:
                log.warning('Could not check why SoChain refused the API key due to %s', e)
                return

            if api_key != self._get_api_key():
                return

            if status_code == HTTPStatus.OK:
                log.warning('The SoChain allowance is used up. Not asking it until 00:00 UTC')
                self.unavailable_until = (
                    time.monotonic() + DAY_IN_SECONDS - ts_now() % DAY_IN_SECONDS
                )
            elif status_code == HTTPStatus.UNAUTHORIZED:
                self.reported_key_as_not_usable = True
                self.db.msg_aggregator.add_missing_key_message(
                    service=self.service_name,
                    location=str(SupportedBlockchain.DOGECOIN),
                    reason='key_not_usable',
                )

    def _query_with_key(self, url: str) -> dict[str, Any]:
        """Query the given url with the API key, if there is one.

        May raise:
        - RemoteError if the query fails. See _query.
        """
        api_key = self._get_api_key()
        try:
            return self._query(
                url=url,
                headers={'API-KEY': api_key} if api_key is not None else None,
            )
        except RemoteError as e:
            if api_key is not None and e.error_code == HTTPStatus.UNAUTHORIZED:
                self._handle_refused_key(api_key)
            raise

    def get_balance(self, address: BTCAddress) -> FVal:
        """Query the confirmed balance of an address, in whole coins.
        https://sochain.com/docs/balance

        May raise:
        - RemoteError if the query fails or its response can't be deserialized.
        """
        data = self._query_with_key(url=f'{SOCHAIN_BASE_URL}/balance/{self.network}/{address}')
        if (confirmed := data.get('confirmed')) is None:
            raise RemoteError(
                f'Unexpected SoChain {self.network} balance response for {address}: '
                f"missing key 'confirmed'. Response data: {data}",
                cause=FailureCause.BAD_DATA,
            )

        return self._deserialize_balance(value=confirmed, address=address)
