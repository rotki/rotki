"""Session-cookie auth (Docker deployment).

core mints a signed `rotki_session` HttpOnly cookie on `authenticate`/create and
gates every non-allowlisted route on it (deny-by-default), enforcing that the
cookie's `sid` is the single active session (so a new login revokes old windows —
#3156). These tests drive a live server with the session key set on the fixture's
`rest_api` (the same live-attribute trick the backend tests use), so the gate is
exercised end-to-end through real HTTP.
"""
import time
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus
from threading import Event
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.api.session_store import SESSION_DB_NAME, SessionStore
from rotkehlchen.api.session_token import (
    MCP_BACKEND_PROOF_HEADER,
    SESSION_COOKIE_NAME,
    SESSION_IDLE_TTL,
    create_mcp_backend_proof,
    mint_session_token,
    read_mcp_token,
    read_session_token,
    verify_session_token,
)
from rotkehlchen.constants.misc import GLOBALDIR_NAME
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_sync_response_with_result,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.api.server import APIServer

SESSION_KEY = b'a-test-session-signing-key'


class _BlockedSessionLogin:
    def __init__(self, login: Callable[[str], str]) -> None:
        self.login = login
        self.entered = Event()
        self.release = Event()

    def __call__(self, username: str) -> str:
        self.entered.set()
        assert self.release.wait(timeout=10)
        return self.login(username)


class _BlockedAsyncQuery:
    def __init__(self) -> None:
        self.release = Event()

    def __call__(self, *_args: Any, **_kwargs: Any) -> None:
        assert self.release.wait(timeout=10)


def _enable_session(api_server: APIServer) -> SessionStore:
    """Turn the cookie gate on live: set the key and build a real SessionStore (the
    server started without the env key, so its store is None). Mirrors production wiring
    at rest_api.__init__ but at test time. Returns the store for introspection."""
    rest_api = api_server.rest_api
    rest_api.session_key = SESSION_KEY
    store = SessionStore(
        db_path=rest_api.rotkehlchen.data_dir / GLOBALDIR_NAME / SESSION_DB_NAME,
        session_key=SESSION_KEY,
    )
    rest_api.session_store = store
    return store


def _disable_session(api_server: APIServer) -> None:
    """Turn the gate back off and close the store (test cleanup)."""
    rest_api = api_server.rest_api
    if rest_api.session_store is not None:
        rest_api.session_store.close()
    rest_api.session_key = None
    rest_api.session_store = None


def _cookie_sid(token: str) -> str:
    """The sid carried by a session cookie token."""
    claims = read_session_token(SESSION_KEY, token)
    assert claims is not None
    return claims.sid


def _logout(api_server: APIServer, username: str) -> None:
    requests.patch(
        api_url_for(api_server, 'usersbynameresource', name=username),
        json={'action': 'logout'},
    )


# --- pure token verify ------------------------------------------------------

def test_verify_session_token_roundtrip_and_failures() -> None:
    key = b'the-key'
    token = mint_session_token(key, 'alice', 'sid-1')['token']
    assert verify_session_token(key, token) == 'alice'  # happy path
    assert verify_session_token(b'other-key', token) is None  # wrong key
    assert verify_session_token(key, 'not-a-token') is None  # malformed
    assert verify_session_token(key, token + 'x') is None  # tampered signature

    minted = mint_session_token(key, 'bob', 'sid-2', now=1_000)
    assert verify_session_token(key, minted['token'], now=1_001) == 'bob'  # inside window
    assert verify_session_token(key, minted['token'], now=minted['exp']) is None  # at exp
    assert verify_session_token(key, minted['token'], now=minted['exp'] + 1) is None  # expired


# --- authenticate sets the cookie, no token in body -------------------------

@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_authenticate_sets_cookie_for_correct_password(
        rotkehlchen_api_server: APIServer,
        username: str,
) -> None:
    """authenticate validates the password and ships a signed HttpOnly cookie; the
    token is never in the body. A wrong password is rejected early."""
    _logout(rotkehlchen_api_server, username)
    store = _enable_session(rotkehlchen_api_server)
    url = api_url_for(rotkehlchen_api_server, 'userauthenticateresource', name=username)
    try:
        # wrong password ⇒ 401, no cookie
        wrong = requests.post(url, json={'password': 'wrongpass'})
        assert_error_response(response=wrong, status_code=HTTPStatus.UNAUTHORIZED)
        assert SESSION_COOKIE_NAME not in wrong.cookies

        # correct password ⇒ 200, empty body, a valid signed cookie bound to the user
        response = requests.post(url, json={'password': '123'})
        result = assert_proper_sync_response_with_result(response)
        assert result == {}  # token redacted from the body
        cookie = response.cookies.get(SESSION_COOKIE_NAME)
        assert cookie is not None
        assert verify_session_token(SESSION_KEY, cookie) == username
        # a fresh active session was opened, and the cookie carries its sid
        assert store.is_active(username, _cookie_sid(cookie)) is True
        # HttpOnly so JS can't read it
        set_cookie_header = response.headers['Set-Cookie']
        assert 'HttpOnly' in set_cookie_header
        assert 'SameSite=Lax' in set_cookie_header
    finally:
        _disable_session(rotkehlchen_api_server)


@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_authenticate_is_inert_without_a_key(
        rotkehlchen_api_server: APIServer,
        username: str,
) -> None:
    """No session key ⇒ the feature is off: authenticate returns success without
    checking the password or setting a cookie (Electron/dev behave as today)."""
    _logout(rotkehlchen_api_server, username)
    rest_api = rotkehlchen_api_server.rest_api
    assert rest_api.session_key is None
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'userauthenticateresource', name=username),
        json={'password': 'does-not-matter'},
    )
    assert assert_proper_sync_response_with_result(response) == {}
    assert SESSION_COOKIE_NAME not in response.cookies


# --- the gate: deny-by-default + cookie-less allowlist ----------------------

@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_cookie_gate(rotkehlchen_api_server: APIServer, username: str) -> None:
    """A gated route needs the cookie; the cookie-less allowlist does not; a valid
    cookie lets a gated route through; logout drops the cookie and the active sid."""
    store = _enable_session(rotkehlchen_api_server)
    settings_url = api_url_for(rotkehlchen_api_server, 'settingsresource')
    try:
        session = requests.Session()

        # gated route without a cookie ⇒ 401
        assert_error_response(
            response=session.get(settings_url),
            status_code=HTTPStatus.UNAUTHORIZED,
        )

        # the cookie-less allowlist is reachable without a cookie
        for resource in ('pingresource', 'inforesource', 'usersresource'):
            assert session.get(api_url_for(rotkehlchen_api_server, resource)).status_code != \
                HTTPStatus.UNAUTHORIZED

        # authenticate (user logged in, same user, password verified) sets the
        # cookie on the session, after which the gated route passes.
        auth_url = api_url_for(rotkehlchen_api_server, 'userauthenticateresource', name=username)
        session.post(auth_url, json={'password': '123'})
        assert SESSION_COOKIE_NAME in session.cookies
        sid = _cookie_sid(session.cookies[SESSION_COOKIE_NAME])

        assert session.get(settings_url).status_code == HTTPStatus.OK

        # logout clears the cookie ⇒ the browser drops it from its jar and the
        # server-side session is revoked (the sid is no longer active)
        logout_url = api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username)
        assert session.patch(logout_url, json={'action': 'logout'}).status_code == HTTPStatus.OK
        assert SESSION_COOKIE_NAME not in session.cookies
        assert store.is_active(username, sid) is False
    finally:
        _disable_session(rotkehlchen_api_server)


@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_issue_mcp_bearer_token(
        rotkehlchen_api_server: APIServer,
        username: str,
) -> None:
    """Only an authenticated active session can obtain an MCP bearer token."""
    store = _enable_session(rotkehlchen_api_server)
    token_url = api_url_for(rotkehlchen_api_server, 'mcptokenresource')
    try:
        session = requests.Session()
        assert_error_response(
            response=session.post(token_url),
            status_code=HTTPStatus.UNAUTHORIZED,
        )

        session.cookies.set(SESSION_COOKIE_NAME, store.login(username))
        response = session.post(token_url)
        result = assert_proper_sync_response_with_result(response)
        assert response.headers['Cache-Control'] == 'no-store'
        assert response.headers['Pragma'] == 'no-cache'
        assert result['token_type'] == 'Bearer'
        assert isinstance(result['expires_at'], int)
        token = result['access_token']
        assert read_session_token(SESSION_KEY, token) is None
        claims = read_mcp_token(SESSION_KEY, token)
        assert claims is not None
        assert claims.username == username
        assert store.is_active(username=username, sid=claims.sid) is True

        settings_url = api_url_for(rotkehlchen_api_server, 'settingsresource')
        assert requests.get(
            settings_url,
            cookies={SESSION_COOKIE_NAME: token},
        ).status_code == HTTPStatus.UNAUTHORIZED
        assert requests.get(
            settings_url,
            headers={'Authorization': f'Bearer {token}'},
        ).status_code == HTTPStatus.UNAUTHORIZED
        internal_headers = {
            'Authorization': f'Bearer {token}',
            MCP_BACKEND_PROOF_HEADER: create_mcp_backend_proof(key=SESSION_KEY, token=token),
        }
        assert requests.get(settings_url, headers=internal_headers).status_code == HTTPStatus.OK

        store.revoke(username)
        assert store.is_active(username=username, sid=claims.sid) is False
        assert requests.get(
            settings_url,
            headers=internal_headers,
        ).status_code == HTTPStatus.UNAUTHORIZED
    finally:
        _disable_session(rotkehlchen_api_server)


@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_cookie_less_patch_user_is_gated(
        rotkehlchen_api_server: APIServer,
        username: str,
) -> None:
    """`PATCH /users/<name>` shares its rule with POST (login), but PATCH changes
    premium credentials / logs out. A cookie-less PATCH must 401 at the gate even
    while a user is logged in — otherwise `require_loggedin_user` (which only checks
    that *some* user is logged in) would let the network replace premium credentials
    or force a logout by name (the name is enumerable via the open `GET /users`)."""
    _enable_session(rotkehlchen_api_server)
    user_url = api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username)
    try:
        session = requests.Session()  # no cookie
        # premium-credential replacement is rejected before reaching the resource
        assert_error_response(
            response=session.patch(
                user_url,
                json={'premium_api_key': 'a' * 40, 'premium_api_secret': 'b' * 40},
            ),
            status_code=HTTPStatus.UNAUTHORIZED,
        )
        # force-logout by name is likewise rejected at the gate
        assert_error_response(
            response=session.patch(user_url, json={'action': 'logout'}),
            status_code=HTTPStatus.UNAUTHORIZED,
        )
    finally:
        _disable_session(rotkehlchen_api_server)


@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_rolling_refresh(rotkehlchen_api_server: APIServer, username: str) -> None:
    """An authenticated request re-issues the cookie only once it is past half its
    lifetime — a fresh cookie is left untouched (no Set-Cookie on every response)."""
    store = _enable_session(rotkehlchen_api_server)
    settings_url = api_url_for(rotkehlchen_api_server, 'settingsresource')
    now = int(time.time())
    try:
        session = requests.Session()

        # a real active session; its fresh token sits well within the idle window ⇒
        # gated passes, not re-issued
        fresh_token = store.login(username)
        sid = _cookie_sid(fresh_token)
        session.cookies.set(SESSION_COOKIE_NAME, fresh_token)
        fresh = session.get(settings_url)
        assert fresh.status_code == HTTPStatus.OK
        assert SESSION_COOKIE_NAME not in fresh.cookies

        # a cookie for the *same* active sid but whose exp is already past half the
        # idle window (not yet expired) ⇒ the response rolls it forward
        old_token = mint_session_token(
            SESSION_KEY,
            username,
            sid,
            expires_at=now + SESSION_IDLE_TTL // 4,  # < now + IDLE/2 ⇒ triggers refresh
        )['token']
        session.cookies.set(SESSION_COOKIE_NAME, old_token)
        refreshed = session.get(settings_url)
        assert refreshed.status_code == HTTPStatus.OK
        assert SESSION_COOKIE_NAME in refreshed.cookies
    finally:
        _disable_session(rotkehlchen_api_server)


# --- single-session: sid rotation / termination (#3156) ---------------------

@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_new_session_rotates_sid_and_kicks_the_old_window(
        rotkehlchen_api_server: APIServer,
        username: str,
) -> None:
    """A new-location login (same user, no cookie) rotates the active sid: the
    first window's cookie now fails the gate (401 → login) while the new one
    passes. This is the #3156 termination for the same-user case."""
    store = _enable_session(rotkehlchen_api_server)
    settings_url = api_url_for(rotkehlchen_api_server, 'settingsresource')
    auth_url = api_url_for(rotkehlchen_api_server, 'userauthenticateresource', name=username)
    try:
        first = requests.Session()
        first.post(auth_url, json={'password': '123'})
        assert first.get(settings_url).status_code == HTTPStatus.OK
        first_sid = _cookie_sid(first.cookies[SESSION_COOKIE_NAME])

        # a second browser (fresh jar, no cookie) logs in as the same user ⇒ takeover
        second = requests.Session()
        second.post(auth_url, json={'password': '123'})
        second_sid = _cookie_sid(second.cookies[SESSION_COOKIE_NAME])
        assert second_sid != first_sid
        assert store.active_sid(username) == second_sid  # the store now holds the new sid

        # the first window's cookie is now stale ⇒ gated route 401s (→ login)
        assert_error_response(
            response=first.get(settings_url),
            status_code=HTTPStatus.UNAUTHORIZED,
        )
        # the new window passes
        assert second.get(settings_url).status_code == HTTPStatus.OK

        # the takeover must not leave the api-task kill switch latched: the new
        # window's async queries have to actually run, not be cancelled at spawn
        assert rotkehlchen_api_server.rest_api.api_tasks_stop_reason is None
        task_id = assert_ok_async_response(second.get(
            api_url_for(rotkehlchen_api_server, 'blockchainbalancesresource'),
            json={'async_query': True},
        ))
        deadline = time.monotonic() + 30
        while True:  # poll through `second` since the async-tasks route is cookie-gated
            assert time.monotonic() < deadline, f'timed out waiting for task id {task_id}'
            result = second.get(api_url_for(
                rotkehlchen_api_server,
                'specific_async_tasks_resource',
                task_id=task_id,
            )).json()['result']
            if result['status'] == 'completed':
                break
            time.sleep(.2)
        assert result['outcome']['result'] is not None
    finally:
        _disable_session(rotkehlchen_api_server)


@pytest.mark.parametrize('start_with_logged_in_user', [True])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_session_takeover_keeps_old_session_async_tasks_stopped(
        rotkehlchen_api_server: APIServer,
        username: str,
) -> None:
    """An old cookie must not spawn an uncancelled task while takeover rotates its sid."""
    rest_api = rotkehlchen_api_server.rest_api
    store = _enable_session(rotkehlchen_api_server)
    auth_url = api_url_for(rotkehlchen_api_server, 'userauthenticateresource', name=username)
    balances_url = api_url_for(rotkehlchen_api_server, 'blockchainbalancesresource')
    first, second = requests.Session(), requests.Session()
    first.post(auth_url, json={'password': '123'})
    blocked_login = _BlockedSessionLogin(store.login)
    blocked_query = _BlockedAsyncQuery()
    try:
        with (
            patch.object(store, 'login', side_effect=blocked_login),
            patch.object(rest_api, '_do_query_async', side_effect=blocked_query),
            ThreadPoolExecutor(max_workers=1) as executor,
        ):
            takeover = executor.submit(second.post, auth_url, json={'password': '123'})
            assert blocked_login.entered.wait(timeout=10)

            assert_ok_async_response(first.get(balances_url, json={'async_query': True}))
            with rest_api.task_lock:
                escaped_task = rest_api.rotkehlchen.api_tasks[-1]

            blocked_login.release.set()
            assert takeover.result(timeout=10).status_code == HTTPStatus.OK
            assert escaped_task.cancellation_token is not None
            assert escaped_task.cancellation_token.cancelled is True
    finally:
        blocked_login.release.set()
        blocked_query.release.set()
        _disable_session(rotkehlchen_api_server)


@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_reload_with_cookie_keeps_sid_and_pending_tasks(
        rotkehlchen_api_server: APIServer,
        username: str,
) -> None:
    """A same-browser reload carries the cookie (sid == active): authenticate
    re-issues with the *same* sid and does not cancel pending tasks (don't kick
    your own tabs). A takeover without the cookie rotates the sid and clears tasks."""
    rest_api = rotkehlchen_api_server.rest_api
    store = _enable_session(rotkehlchen_api_server)
    auth_url = api_url_for(rotkehlchen_api_server, 'userauthenticateresource', name=username)
    try:
        session = requests.Session()
        session.post(auth_url, json={'password': '123'})
        sid = store.active_sid(username)

        # reload: the cookie rides the request ⇒ same sid, tasks untouched
        rest_api.task_results = {42: 'pending'}
        session.post(auth_url, json={'password': '123'})
        assert store.active_sid(username) == sid
        assert rest_api.task_results == {42: 'pending'}

        # takeover from a fresh jar ⇒ rotate sid and clear the previous tasks
        other = requests.Session()
        other.post(auth_url, json={'password': '123'})
        assert store.active_sid(username) != sid
        assert rest_api.task_results == {}
    finally:
        _disable_session(rotkehlchen_api_server)


@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_authenticate_different_user_conflicts(
        rotkehlchen_api_server: APIServer,
        username: str,
) -> None:
    """While a user is logged in, authenticating as a *different* user is a 409
    conflict (the existing single-user behaviour) — not a takeover."""
    store = _enable_session(rotkehlchen_api_server)
    try:
        response = requests.post(
            api_url_for(rotkehlchen_api_server, 'userauthenticateresource', name='someone_else'),
            json={'password': '123'},
        )
        assert_error_response(response=response, status_code=HTTPStatus.CONFLICT)
        assert store.active_sid('someone_else') is None  # no session opened
    finally:
        _disable_session(rotkehlchen_api_server)


@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_failed_create_while_logged_in_keeps_the_live_session(
        rotkehlchen_api_server: APIServer,
        username: str,
) -> None:
    """Creating an account while a user is logged in 409s — and must not touch the
    session store. The mint is skipped, so the logged-in user's active session is
    neither kicked (create is cookie-less/network-reachable in Docker) nor replaced
    by a phantom session for a user that was never created."""
    store = _enable_session(rotkehlchen_api_server)
    settings_url = api_url_for(rotkehlchen_api_server, 'settingsresource')
    auth_url = api_url_for(rotkehlchen_api_server, 'userauthenticateresource', name=username)
    try:
        session = requests.Session()
        session.post(auth_url, json={'password': '123'})
        live_sid = store.active_sid(username)
        assert live_sid is not None

        # attempt to create an account with the same name ⇒ 409, must not rotate the sid
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'usersresource'),
            json={'name': username, 'password': '123'},
        )
        assert_error_response(response=response, status_code=HTTPStatus.CONFLICT)
        assert SESSION_COOKIE_NAME not in response.cookies  # no session minted
        assert store.active_sid(username) == live_sid  # the live session is untouched
        assert session.get(settings_url).status_code == HTTPStatus.OK  # not kicked → login
    finally:
        _disable_session(rotkehlchen_api_server)


@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_failed_create_revokes_the_minted_session(
        rotkehlchen_api_server: APIServer,
) -> None:
    """With no user logged in a create mints the session up front (so its gated
    `/tasks` poll carries the cookie), but if the create then fails the session is
    revoked — a failed create leaves nothing live for a user that never existed."""
    store = _enable_session(rotkehlchen_api_server)
    try:
        # a premium api key without its secret fails create with a 400 *after* the mint
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'usersresource'),
            json={'name': 'ghost', 'password': '123', 'premium_api_key': 'x'},
        )
        assert_error_response(response=response, status_code=HTTPStatus.BAD_REQUEST)
        assert SESSION_COOKIE_NAME not in response.cookies  # no live cookie shipped
        assert store.active_sid('ghost') is None  # the minted session was revoked
    finally:
        _disable_session(rotkehlchen_api_server)


def test_cookie_less_rules_all_exist(rotkehlchen_api_server: APIServer) -> None:
    """Anti-drift: every (rule, method) in the cookie-less allowlist is a real
    registered route/verb. A typo/rename would make an allowlist entry dead —
    silently gating an endpoint the login screen needs — so pin it to the url map."""
    registered = {
        (rule.rule, method)
        for rule in rotkehlchen_api_server.flask_app.url_map.iter_rules()
        for method in (rule.methods or set())
    }
    missing = rotkehlchen_api_server._cookie_less_rules - registered
    assert missing == set(), f'cookie-less allowlist references unknown routes: {missing}'


def test_cookie_less_rules_pinned(rotkehlchen_api_server: APIServer) -> None:
    """Anti-drift: pin the *exact* set of pre-auth-reachable (rule, method) pairs.
    Everything else is deny-by-default once a session key is set, so adding/removing
    an entry widens or narrows what the unauthenticated network can reach — a
    deliberate, security-sensitive change that must show up as a test diff for review.
    Note PATCH on `/users/<name>` is deliberately absent: it changes premium
    credentials / logs out and must stay gated, even though POST (login) is open."""
    prefix = rotkehlchen_api_server._api_prefix
    assert rotkehlchen_api_server._cookie_less_rules == frozenset({
        (f'{prefix}/ping', 'GET'),
        (f'{prefix}/info', 'GET'),
        (f'{prefix}/users', 'GET'),
        (f'{prefix}/users', 'PUT'),
        (f'{prefix}/users/<string:name>', 'POST'),
        (f'{prefix}/users/<string:name>/authenticate', 'POST'),
    })
