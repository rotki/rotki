from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final, Literal

import requests
from mcp.server.auth.middleware.auth_context import get_access_token

from rotkehlchen.api.session_token import MCP_BACKEND_PROOF_HEADER, create_mcp_backend_proof

if TYPE_CHECKING:
    from rotkehlchen.mcp.constants import PrivacyMode

DEFAULT_BACKEND_HOST: Final = '127.0.0.1'
DEFAULT_BACKEND_PORT: Final = 4242
DEFAULT_BACKEND_URL: Final = f'http://{DEFAULT_BACKEND_HOST}:{DEFAULT_BACKEND_PORT}/api/1'
DEFAULT_PRIVACY_MODE: Final[PrivacyMode] = 'balanced'


@dataclass(frozen=True)
class BackendConfig:
    base_url: str
    timeout: int
    session_key: bytes | None = None
    privacy_mode: PrivacyMode = DEFAULT_PRIVACY_MODE
    # Optional cap on how many history events a single analytics load pulls in. None means
    # no cap (load the complete set) so users get complete data by default; set it only to
    # bound load time/cost on a very large history.
    max_events: int | None = None


_backend_config = BackendConfig(base_url=DEFAULT_BACKEND_URL, timeout=5)


class BackendQueryError(Exception):
    """Raised when the local rotki backend cannot be queried."""


def configure_backend(
        base_url: str,
        timeout: int,
        session_key: bytes | None = None,
        privacy_mode: PrivacyMode = DEFAULT_PRIVACY_MODE,
        max_events: int | None = None,
) -> None:
    global _backend_config  # noqa: PLW0603  -- MCP server startup config for registered tools
    _backend_config = BackendConfig(
        base_url=base_url,
        timeout=timeout,
        session_key=session_key,
        privacy_mode=privacy_mode,
        max_events=max_events,
    )


def get_backend_config() -> BackendConfig:
    return _backend_config


def _api_url(base_url: str, endpoint: str) -> str:
    return f'{base_url.rstrip("/")}/{endpoint.lstrip("/")}'


def request_api(
        base_url: str,
        endpoint: str,
        timeout: int,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        method: Literal['GET', 'POST'] = 'GET',
) -> dict[str, Any]:
    """Query the local rotki REST API and return its decoded ``{result, message}`` payload.

    ``method`` selects the verb: plain reads use ``GET`` (with ``params`` for the query
    string), while endpoints that take a filter body (e.g. ``/history/events``) use
    ``POST`` with ``json_data``. Any failure to reach, or make sense of, the backend is
    surfaced as a ``BackendQueryError`` so tools can fail closed.
    """
    url = _api_url(base_url=base_url, endpoint=endpoint)
    request = requests.post if method == 'POST' else requests.get
    headers: dict[str, str] | None = None
    if (
        (access_token := get_access_token()) is not None and
        (session_key := get_backend_config().session_key) is not None
    ):
        headers = {
            'Authorization': f'Bearer {access_token.token}',
            MCP_BACKEND_PROOF_HEADER: create_mcp_backend_proof(
                key=session_key,
                token=access_token.token,
            ),
        }
    try:
        response = request(
            url=url,
            params=params,
            json=json_data,
            timeout=timeout,
            headers=headers,
        )
    except requests.exceptions.RequestException as e:
        raise BackendQueryError(f'Could not connect to rotki backend at {url}: {e!s}') from e

    if response.status_code != HTTPStatus.OK:
        raise BackendQueryError(
            f'rotki backend returned HTTP {response.status_code} for {url}: {response.text}',
        )

    try:
        payload = response.json()
    except ValueError as e:
        raise BackendQueryError(f'rotki backend returned invalid JSON for {url}: {e!s}') from e

    if not isinstance(payload, dict) or 'result' not in payload:
        raise BackendQueryError(f'rotki backend returned an unexpected response for {url}')

    return payload


def query_history_events_page(
        limit: int,
        offset: int,
        from_timestamp: int | None = None,
        to_timestamp: int | None = None,
        exclude_ignored_assets: bool = True,
        aggregate_by_group_ids: bool = False,
) -> dict[str, Any]:
    """Fetch one page of decoded history events. Used by the analytics loader to page the
    full (time-scoped) set into a local frame. Returns the backend ``result`` dict.

    ``aggregate_by_group_ids`` collapses each group to its first event plus a
    ``grouped_events_num`` count; it is only sent when set, so the default request body is
    unchanged.
    """
    backend_config = get_backend_config()
    body: dict[str, Any] = {
        'limit': limit,
        'offset': offset,
        'exclude_ignored_assets': exclude_ignored_assets,
    }
    if aggregate_by_group_ids:
        body['aggregate_by_group_ids'] = True
    if from_timestamp is not None:
        body['from_timestamp'] = from_timestamp
    if to_timestamp is not None:
        body['to_timestamp'] = to_timestamp

    payload = request_api(
        base_url=backend_config.base_url,
        endpoint='history/events',
        timeout=backend_config.timeout,
        json_data=body,
        method='POST',
    )
    return payload['result']


def query_settings() -> dict[str, Any]:
    """Return the user's settings. The analytics layer reads ``main_currency`` from here so
    that valued events are denominated the same way the rest of rotki denominates them.
    """
    backend_config = get_backend_config()
    payload = request_api(
        base_url=backend_config.base_url,
        endpoint='settings',
        timeout=backend_config.timeout,
    )
    if not isinstance(result := payload['result'], dict):
        raise BackendQueryError('rotki backend returned an unexpected settings response')

    return result


def query_all_balances(refresh: bool, timeout: int) -> dict[str, Any]:
    """Return the current balances snapshot. ``refresh=True`` forces a slow live query of
    every exchange and chain; otherwise the cached snapshot is returned. Read-only: never
    persists. Returns the backend ``result`` dict.
    """
    backend_config = get_backend_config()
    payload = request_api(
        base_url=backend_config.base_url,
        endpoint='balances',
        timeout=timeout,
        params={'ignore_cache': 'true'} if refresh else None,
    )
    return payload['result']


def query_asset_details(identifiers: list[str]) -> dict[str, Any]:
    """Return GlobalDB details for the requested asset identifiers."""
    if len(identifiers) == 0:
        raise ValueError('At least one asset identifier is required')

    backend_config = get_backend_config()
    payload = request_api(
        base_url=backend_config.base_url,
        endpoint='assets/all',
        timeout=backend_config.timeout,
        json_data={'identifiers': identifiers},
        method='POST',
    )
    if not isinstance(result := payload['result'], dict) or not isinstance(
            result.get('entries'),
            list,
    ):
        raise BackendQueryError('rotki backend returned an unexpected assets response')

    return result


def query_historical_prices(
        asset_timestamps: list[tuple[str, int]],
        target_asset: str,
        max_seconds_distance: int,
) -> dict[str, Any]:
    """Return prices stored in GlobalDB near the requested timestamps."""
    if len(asset_timestamps) == 0:
        raise ValueError('At least one asset and timestamp pair is required')
    if max_seconds_distance <= 0:
        raise ValueError('Maximum seconds distance must be positive')

    backend_config = get_backend_config()
    payload = request_api(
        base_url=backend_config.base_url,
        endpoint='assets/prices/historical',
        timeout=backend_config.timeout,
        json_data={
            'assets_timestamp': asset_timestamps,
            'target_asset': target_asset,
            'only_cache_period': max_seconds_distance,
        },
        method='POST',
    )
    if (
        not isinstance(result := payload['result'], dict) or
        not isinstance(result.get('assets'), dict) or
        not isinstance(result.get('target_asset'), str)
    ):
        raise BackendQueryError(
            'rotki backend returned an unexpected historical prices response',
        )

    return result
