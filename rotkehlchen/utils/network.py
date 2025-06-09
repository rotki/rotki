import json
import logging
from collections.abc import Callable
from http import HTTPStatus
from typing import Any, Literal, overload

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from rotkehlchen.constants import GLOBAL_REQUESTS_TIMEOUT
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.concurrency import sleep

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def create_session(max_backoff_secs: float = 30) -> requests.Session:
    """Create a requests session configured to retry on connection, read, and
    specific server errors.

    Retries up to 3 times for connection errors (e.g., timeouts, DNS failures), 2 times for
    read errors, and 1 time for specified server errors (502, 503, 504). Users must check
    response status codes manually, as bad statuses outside the retry list are not
    automatically retried.

    From the requests docs about max_retries:
    The maximum number of retries each connection should attempt. Note, this applies only
    to failed DNS lookups, socket connections and connection timeouts, never to requests
    where data has made it to the server.
    """
    session = requests.Session()
    # we don't use total in the adapter because it seems to trigger on certain bad status codes
    # like too many requests even when status_forcelist is set to an empty list. This
    # configuration worked fine for what we could test in real scenarios in the e2e tests.
    adapter = HTTPAdapter(max_retries=Retry(
        # Total retry attempts across all error types (connection, read, status, etc.). As
        # mentioned in the docs:
        # Set to None to remove this constraint and fall back on other counts.
        total=None,
        # Retries for connection errors (e.g., timeouts, refused connections).
        connect=3,
        # Retries for read errors (e.g., incomplete responses or dropped connections).
        read=2,
        # Retries for HTTP status codes listed in status_forcelist.
        status=1,
        # Don't allow any other type of error. This will warn us about any possible
        # error not handled.
        other=0,
        # Don't raise exceptions on retryable status codes; return the response instead
        # for manual handling.
        raise_on_status=False,
        # Retry only on idempotent methods to avoid side effects.
        allowed_methods={'DELETE', 'GET', 'HEAD', 'OPTIONS', 'PUT', 'TRACE'},
        # Limit redirects to 2 hops to avoid infinite redirect loops.
        redirect=2,
        # by default urllib retries on 413, 429 (rate limit) and 503. Set it so we only retry
        # on server errors.
        status_forcelist=[
            502,  # Bad Gateway
            503,  # Service not available
            504,  # Gateway Timeout
        ],
        # Maximum seconds between retries if backoff is enabled (currently irrelevant
        # with backoff_factor=0).
        backoff_max=max_backoff_secs,  # type: ignore[call-arg]  # mypy doesn't seem to detect this one
        # Backoff in retry follows the formula
        # {backoff factor} * (2 ** ({number of previous retries}))
        # since we only care about connection errors/read errors that are solved just by
        # retrying set a low one.
        backoff_factor=1,
    ))
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def request_get(
        url: str,
        timeout: int = GLOBAL_REQUESTS_TIMEOUT,
        handle_429: bool = False,
        backoff_in_seconds: float = 0,
) -> dict | list:
    """
    May raise:
    - UnableToDecryptRemoteData from request_get
    - Remote error if the get request fails
    """
    log.debug(f'Querying {url}')
    # TODO make this a bit more smart. Perhaps conditional on the type of request.
    # Not all requests would need repeated attempts
    response = retry_calls(
        times=CachedSettings().get_query_retry_limit(),
        location='',
        handle_429=handle_429,
        backoff_in_seconds=backoff_in_seconds,
        method_name=url,
        function=requests.get,
        # function's arguments
        url=url,
        timeout=timeout,
    )

    if response.status_code != HTTPStatus.OK:
        raise RemoteError(f'{url} returned status: {response.status_code}')

    try:
        result = json.loads(response.text)
    except json.decoder.JSONDecodeError as e:
        raise UnableToDecryptRemoteData(f'{url} returned malformed json. Error: {e!s}') from e

    return result


def request_get_dict(
        url: str,
        timeout: int = GLOBAL_REQUESTS_TIMEOUT,
        handle_429: bool = False,
        backoff_in_seconds: float = 0,
) -> dict:
    """Like request_get, but the endpoint only returns a dict

    May raise:
    - UnableToDecryptRemoteData from request_get
    - Remote error if the get request fails
    """
    response = request_get(url, timeout, handle_429, backoff_in_seconds)
    assert isinstance(response, dict)  # pylint: disable=isinstance-second-argument-not-valid-type
    return response


def retry_calls(
        times: int,
        location: str,
        handle_429: bool,
        backoff_in_seconds: float,
        method_name: str,
        function: Callable[..., Any],
        **kwargs: Any,
) -> Any:
    """Calls a function that deals with external apis for a given number of times
    until it fails or until it succeeds.

    If it fails with an acceptable error then we wait for a bit until the next try.

    Can also handle 429 errors with a specific backoff in seconds if required.

    - Raises RemoteError if there is something wrong with contacting the remote
    """
    tries = times
    while True:
        try:
            result = function(**kwargs)

            if handle_429 and result.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                if tries == 0:
                    raise RemoteError(
                        f'{location} query for {method_name} failed after {times} tries',
                    )

                log.debug(
                    f'In retry_call for {location}-{method_name}. Got 429. Backing off for '
                    f'{backoff_in_seconds} seconds',
                )
                sleep(backoff_in_seconds)
                tries -= 1
                continue

            return result  # noqa: TRY300

        except requests.exceptions.RequestException as e:
            tries -= 1
            log.debug(
                f'In retry_call for {location}-{method_name}. Got error {e!s} '
                f'Trying again ... with {tries} tries left',
            )
            if tries == 0:
                raise RemoteError(
                    f'{location} query for {method_name} failed after {times} tries. Reason: {e}') from e  # noqa: E501


@overload
def query_file(url: str, is_json: Literal[True]) -> dict[str, Any]:
    ...


@overload
def query_file(url: str, is_json: Literal[False]) -> str:
    ...


def query_file(url: str, is_json: bool = False) -> str | dict[str, Any]:
    """
    Query the given file url and return the contents of the file
    May raise:
    - RemoteError if it was not possible to query the remote or the file is not a valid json file
    and is_json is set to true.
    """
    try:
        response = requests.get(url=url, timeout=CachedSettings().get_timeout_tuple())
    except requests.exceptions.RequestException as e:
        raise RemoteError(f'Failed to query file {url} due to: {e!s}') from e

    if response.status_code != 200:
        raise RemoteError(
            message=(
                f'File query for {url} failed with status code '
                f'{response.status_code} and text: {response.text}'
            ),
            error_code=response.status_code,
        )

    if is_json is True:
        try:
            return response.json()
        except json.decoder.JSONDecodeError as e:
            raise RemoteError(f'Queried file {url} is not a valid json file') from e

    return response.text
