from typing import TYPE_CHECKING, Final
from unittest.mock import MagicMock

import pytest

from rotkehlchen.api.server import APIServer

if TYPE_CHECKING:
    from flask.testing import FlaskClient

# The --api-cors lists rotki launches core with. Packaged and dev Electron come from
# `corsOrigins` in frontend/app/shared/starling/starling-args.ts, the starling default
# from crates/starling/src/main.rs and the core default from rotkehlchen/args.py.
PACKAGED_ELECTRON: Final[list[str]] = ['app://localhost', 'http://localhost:*']
DEV_ELECTRON: Final[list[str]] = ['http://localhost:5173', 'http://localhost:*']
STARLING_DEFAULT: Final[list[str]] = ['http://localhost:*/*', 'app://localhost/*']
CORE_DEFAULT: Final[list[str]] = ['http://localhost:*/*']
IPV6_LOOPBACK: Final[list[str]] = ['http://[::1]:*']


def _client(cors_domain_list: list[str]) -> FlaskClient:
    """A test client for a real `APIServer`, with the session-cookie gate inert."""
    api_server = APIServer(
        rest_api=MagicMock(session_key=None),
        ws_notifier=MagicMock(),
        cors_domain_list=cors_domain_list,
    )
    return api_server.flask_app.test_client()


def _allowed_origin(cors_domain_list: list[str], origin: str) -> str | None:
    """Send the browser preflight for a cross-origin call and return the allowed origin."""
    response = _client(cors_domain_list).options(
        '/api/1/ping',
        headers={'Origin': origin, 'Access-Control-Request-Method': 'GET'},
    )
    return response.headers.get('Access-Control-Allow-Origin')


@pytest.mark.parametrize(('cors_domain_list', 'origin'), [
    (PACKAGED_ELECTRON, 'app://localhost'),
    (PACKAGED_ELECTRON, 'http://localhost:4242'),
    (PACKAGED_ELECTRON, 'http://localhost'),
    (DEV_ELECTRON, 'http://localhost:5173'),
    (DEV_ELECTRON, 'http://localhost'),
    (STARLING_DEFAULT, 'app://localhost'),
    (STARLING_DEFAULT, 'http://localhost:5173'),
    (STARLING_DEFAULT, 'http://localhost'),
    (CORE_DEFAULT, 'HTTP://LOCALHOST:4242'),
    (IPV6_LOOPBACK, 'http://[::1]:5173'),
    ([' http://localhost:5173 ', ' app://localhost/* '], 'app://localhost'),
    (['*'], 'https://anything.example.com'),
])
def test_cors_allows_the_frontend_origins(cors_domain_list: list[str], origin: str) -> None:
    assert _allowed_origin(cors_domain_list, origin) == origin


@pytest.mark.parametrize(('cors_domain_list', 'origin'), [
    (PACKAGED_ELECTRON, 'app://evil'),
    (PACKAGED_ELECTRON, 'app://localhost.evil'),
    (PACKAGED_ELECTRON, 'http://localhost.evil.com'),
    (PACKAGED_ELECTRON, 'http://localhostattacker.com'),
    (DEV_ELECTRON, 'http://localhost:5173.evil.com'),
    (STARLING_DEFAULT, 'http://localhost.evil.com'),
    (STARLING_DEFAULT, 'http://localhost:4242.evil.com'),
    (STARLING_DEFAULT, 'app://localhost.evil'),
    (STARLING_DEFAULT, 'app://localhostattacker'),
    (STARLING_DEFAULT, 'https://localhost:5173'),
    (STARLING_DEFAULT, 'null'),
    (CORE_DEFAULT, 'http://localhost.evil.com'),
])
def test_cors_rejects_lookalike_origins(cors_domain_list: list[str], origin: str) -> None:
    assert _allowed_origin(cors_domain_list, origin) is None


def test_cors_warns_about_regex_patterns(caplog: pytest.LogCaptureFixture) -> None:
    _client([r'https://.*\.example\.com'])
    assert 'CORS pattern contains regex syntax' in caplog.text


def test_cors_does_not_warn_about_ipv6_hosts(caplog: pytest.LogCaptureFixture) -> None:
    _client([*IPV6_LOOPBACK, *PACKAGED_ELECTRON, *STARLING_DEFAULT])
    assert 'CORS pattern contains regex syntax' not in caplog.text
