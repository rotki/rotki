from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Final

import requests

from rotkehlchen.api.server import API_PREFIX

DEFAULT_BACKEND_HOST: Final = '127.0.0.1'
DEFAULT_BACKEND_PORT: Final = 4242
DEFAULT_BACKEND_URL: Final = f'http://{DEFAULT_BACKEND_HOST}:{DEFAULT_BACKEND_PORT}{API_PREFIX}'


@dataclass(frozen=True)
class BackendConfig:
    base_url: str
    timeout: int


_backend_config = BackendConfig(base_url=DEFAULT_BACKEND_URL, timeout=5)


class BackendQueryError(Exception):
    """Raised when the local rotki backend cannot be queried."""


def configure_backend(base_url: str, timeout: int) -> None:
    global _backend_config  # noqa: PLW0603  -- MCP server startup config for registered tools
    _backend_config = BackendConfig(base_url=base_url, timeout=timeout)


def get_backend_config() -> BackendConfig:
    return _backend_config


def _api_url(base_url: str, endpoint: str) -> str:
    return f'{base_url.rstrip("/")}/{endpoint.lstrip("/")}'


def request_api(
        base_url: str,
        endpoint: str,
        timeout: int,
        params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = _api_url(base_url=base_url, endpoint=endpoint)
    try:
        response = requests.get(url=url, params=params, timeout=timeout)
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
