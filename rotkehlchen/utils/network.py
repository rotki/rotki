import json
import logging
from collections.abc import Callable
from http import HTTPStatus
from typing import Any, Literal, overload

import gevent
import requests

from rotkehlchen.constants import GLOBAL_REQUESTS_TIMEOUT
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


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
    untils it fails or until it succeeds.

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
                gevent.sleep(backoff_in_seconds)
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
