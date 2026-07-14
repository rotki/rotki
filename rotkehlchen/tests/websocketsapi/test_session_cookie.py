from typing import NamedTuple

from rotkehlchen.api.asgi import _ws_session_allowed
from rotkehlchen.api.session_token import mint_session_token

SESSION_KEY = b'ws-test-session-signing-key'
ACTIVE_SID = 'active-session-id'
ACTIVE_USER = 'alice'


class _FakeSessionStore(NamedTuple):
    """Minimal stand-in exposing the is_active membership check the gate uses."""
    active_sid: str | None

    def is_active(self, username: str, sid: str) -> bool:
        return username == ACTIVE_USER and sid == self.active_sid


class _FakeRestAPI(NamedTuple):
    """Minimal stand-in exposing the attributes the gate reads live."""
    session_key: bytes | None
    session_store: _FakeSessionStore | None


def _scope(cookie: str | None = None) -> dict:
    """An ASGI websocket scope, optionally carrying a Cookie header."""
    headers = [(b'cookie', cookie.encode('latin-1'))] if cookie is not None else []
    return {'type': 'websocket', 'path': '/ws', 'headers': headers}


def test_ws_session_cookie_gate() -> None:
    """The ASGI /ws handshake gate validates the rotki_session cookie (the upgrade
    bypasses Flask's before_request gate). The browser can't set headers on a WS
    handshake but same-origin cookies ride it. Disabled when no key is set; a cookie
    whose sid is not the active one is rejected (single-session, #3156). Returning
    False rejects the handshake *before* accept."""
    # disabled (no key) ⇒ allowed without a cookie
    disabled = _FakeRestAPI(session_key=None, session_store=None)
    assert _ws_session_allowed(disabled, _scope()) is True  # type: ignore[arg-type]  # fake rest api

    rest_api = _FakeRestAPI(
        session_key=SESSION_KEY,
        session_store=_FakeSessionStore(active_sid=ACTIVE_SID),
    )

    # key set, no cookie ⇒ rejected
    assert _ws_session_allowed(rest_api, _scope()) is False  # type: ignore[arg-type]  # fake rest api

    # key set, invalid cookie ⇒ rejected
    assert _ws_session_allowed(rest_api, _scope('rotki_session=garbage')) is False  # type: ignore[arg-type]  # fake rest api

    # key set, valid signature but a stale sid (a previous session) ⇒ rejected
    stale = mint_session_token(SESSION_KEY, 'alice', 'a-different-sid')['token']
    assert _ws_session_allowed(rest_api, _scope(f'rotki_session={stale}')) is False  # type: ignore[arg-type]  # fake rest api

    # key set, valid cookie with the active sid (alongside other cookies) ⇒ allowed
    token = mint_session_token(SESSION_KEY, 'alice', ACTIVE_SID)['token']
    assert _ws_session_allowed(rest_api, _scope(f'theme=dark; rotki_session={token}')) is True  # type: ignore[arg-type]  # fake rest api
