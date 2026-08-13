"""Unit tests for the persistent single-active-session store (Docker cookie auth)."""
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from freezegun import freeze_time

from rotkehlchen.api.session_store import (
    SESSION_DB_NAME,
    SESSION_DB_VERSION,
    SessionStore,
    is_persisted_mcp_session_active,
)
from rotkehlchen.api.session_token import (
    SESSION_ABSOLUTE_TTL,
    SESSION_IDLE_TTL,
    create_mcp_backend_proof,
    read_mcp_token,
    read_session_token,
    verify_mcp_backend_proof,
)

KEY = b'unit-test-session-key'
# 2023-11-14 22:13:20 UTC == 1_700_000_000 unix seconds
BASE = datetime(2023, 11, 14, 22, 13, 20, tzinfo=UTC)
BASE_TS = int(BASE.timestamp())


def _store(tmp_path: Any) -> SessionStore:
    return SessionStore(db_path=tmp_path / SESSION_DB_NAME, session_key=KEY)


@pytest.mark.freeze_time(BASE)
def test_login_mints_active_token(tmp_path: Any) -> None:
    store = _store(tmp_path)
    token = store.login('alice')
    claims = read_session_token(KEY, token)
    assert claims is not None
    assert claims.username == 'alice'
    assert claims.exp == BASE_TS + SESSION_IDLE_TTL  # rolling idle window, not the 7d default
    assert store.is_active('alice', claims.sid) is True


@pytest.mark.freeze_time(BASE)
def test_new_login_kicks_previous_session(tmp_path: Any) -> None:
    store = _store(tmp_path)
    first = read_session_token(KEY, store.login('alice'))
    second = read_session_token(KEY, store.login('alice'))
    assert first is not None and second is not None
    assert first.sid != second.sid
    # takeover: only the newest sid is active; the previous cookie is revoked
    assert store.is_active('alice', first.sid) is False
    assert store.is_active('alice', second.sid) is True


@pytest.mark.freeze_time(BASE)
def test_is_active_rejects_unknown_user_and_wrong_sid(tmp_path: Any) -> None:
    store = _store(tmp_path)
    claims = read_session_token(KEY, store.login('alice'))
    assert claims is not None
    assert store.is_active('bob', claims.sid) is False  # no session for bob
    assert store.is_active('alice', 'deadbeef') is False  # wrong sid


@pytest.mark.freeze_time(BASE)
def test_login_displaces_every_other_user(tmp_path: Any) -> None:
    """A login ends every other user's session, not just the row it upserts.

    Core unlocks one user at a time, so any other row is a session that can no longer
    be reached. Leaving it behind let a displaced user's cookie -- and the MCP bearer
    minted from it, which lives in an external client and is untouched by the browser
    losing its cookie -- outlive the login that displaced them.
    """
    store = _store(tmp_path)
    alice = read_session_token(KEY, store.login('alice'))
    assert alice is not None
    alice_bearer = store.issue_mcp_token(username='alice', sid=alice.sid)
    assert alice_bearer is not None
    assert (alice_mcp := read_mcp_token(KEY, alice_bearer)) is not None

    bob = read_session_token(KEY, store.login('bob'))
    assert bob is not None

    assert store.is_active('alice', alice.sid) is False
    assert store.is_mcp_active(username='alice', sid=alice_mcp.sid) is False
    assert store.is_active('bob', bob.sid) is True
    # gone from the durable mirror too, which is the authority the MCP process reads
    # and the one that survives a restart
    assert is_persisted_mcp_session_active(
        db_path=tmp_path / SESSION_DB_NAME,
        username='alice',
        sid=alice_mcp.sid,
    ) is False


def test_reissue_rolls_exp_and_caps_at_absolute(tmp_path: Any) -> None:
    with freeze_time(BASE):
        store = _store(tmp_path)
        claims = read_session_token(KEY, store.login('alice'))
        assert claims is not None
    # a later request rolls the idle window forward
    later_ts = BASE_TS + SESSION_IDLE_TTL // 2
    with freeze_time(BASE + timedelta(seconds=SESSION_IDLE_TTL // 2)):
        reissued_token = store.reissue('alice', claims.sid)
        assert reissued_token is not None
        rolled = read_session_token(KEY, reissued_token)
        assert rolled is not None
        assert rolled.sid == claims.sid  # same session, not a takeover
        assert rolled.exp == later_ts + SESSION_IDLE_TTL
    # near the absolute ceiling, the rolled exp is capped at abs, never beyond
    with freeze_time(BASE + timedelta(seconds=SESSION_ABSOLUTE_TTL - 10)):
        reissued_token = store.reissue('alice', claims.sid)
        assert reissued_token is not None
        capped = read_session_token(KEY, reissued_token)
        assert capped is not None
        assert capped.exp == BASE_TS + SESSION_ABSOLUTE_TTL


@pytest.mark.freeze_time(BASE)
def test_reissue_rejects_non_active_sid(tmp_path: Any) -> None:
    store = _store(tmp_path)
    store.login('alice')
    assert store.reissue('alice', 'not-the-active-sid') is None
    assert store.reissue('nobody', 'whatever') is None


@pytest.mark.freeze_time(BASE)
def test_mcp_token_is_domain_separated_and_linked_to_session(tmp_path: Any) -> None:
    store = _store(tmp_path)
    session_claims = read_session_token(KEY, store.login('alice'))
    assert session_claims is not None

    token = store.issue_mcp_token(username='alice', sid=session_claims.sid)
    assert token is not None
    assert read_session_token(KEY, token) is None
    assert (mcp_claims := read_mcp_token(KEY, token)) is not None
    assert mcp_claims.username == session_claims.username
    assert mcp_claims.sid != session_claims.sid
    assert mcp_claims.exp == BASE_TS + SESSION_ABSOLUTE_TTL
    assert store.is_mcp_active(mcp_claims.username, mcp_claims.sid) is True

    replacement_token = store.issue_mcp_token(
        username='alice',
        sid=session_claims.sid,
    )
    assert replacement_token is not None
    assert (replacement_claims := read_mcp_token(KEY, replacement_token)) is not None
    assert replacement_claims.sid != mcp_claims.sid
    assert store.is_mcp_active(mcp_claims.username, mcp_claims.sid) is False
    assert store.is_mcp_active(replacement_claims.username, replacement_claims.sid) is True

    proof = create_mcp_backend_proof(key=KEY, token=token)
    assert verify_mcp_backend_proof(key=KEY, token=token, proof=proof) is True
    assert verify_mcp_backend_proof(key=KEY, token=f'{token}x', proof=proof) is False
    assert verify_mcp_backend_proof(key=KEY, token=token, proof='non-ascii-€') is False

    store.revoke('alice')
    assert store.is_mcp_active(replacement_claims.username, replacement_claims.sid) is False


def test_persisted_session_check_closes_connection(tmp_path: Any) -> None:
    connection = MagicMock()
    connection.execute.return_value.fetchone.return_value = (1,)
    with patch('rotkehlchen.api.session_store.sqlite3.connect', return_value=connection):
        assert is_persisted_mcp_session_active(
            db_path=tmp_path / SESSION_DB_NAME,
            username='alice',
            sid='active-sid',
        ) is True
    connection.close.assert_called_once_with()


@pytest.mark.parametrize('token', ['not-ascii-€.signature', 'payload.not-ascii-€'])
def test_read_session_token_rejects_non_ascii_token(token: str) -> None:
    assert read_session_token(KEY, token) is None
    assert read_mcp_token(KEY, token) is None


@pytest.mark.freeze_time(BASE)
def test_revoke_removes_session(tmp_path: Any) -> None:
    store = _store(tmp_path)
    claims = read_session_token(KEY, store.login('alice'))
    assert claims is not None
    store.revoke('alice')
    assert store.is_active('alice', claims.sid) is False


def test_session_survives_restart(tmp_path: Any) -> None:
    db_path = tmp_path / SESSION_DB_NAME
    with freeze_time(BASE):
        claims = read_session_token(KEY, SessionStore(db_path=db_path, session_key=KEY).login('alice'))  # noqa: E501
        assert claims is not None
        # a fresh store on the same file rehydrates the active session from session.db
        reopened = SessionStore(db_path=db_path, session_key=KEY)
        assert reopened.is_active('alice', claims.sid) is True


def test_expired_sessions_pruned_on_load(tmp_path: Any) -> None:
    db_path = tmp_path / SESSION_DB_NAME
    with freeze_time(BASE):
        claims = read_session_token(KEY, SessionStore(db_path=db_path, session_key=KEY).login('alice'))  # noqa: E501
        assert claims is not None
    # reopen well past the absolute ceiling: the row is pruned, session gone
    with freeze_time(BASE + timedelta(seconds=SESSION_ABSOLUTE_TTL + 1)):
        reopened = SessionStore(db_path=db_path, session_key=KEY)
        assert reopened.is_active('alice', claims.sid) is False


@pytest.mark.freeze_time(BASE)
def test_version_mismatch_recreates_table(tmp_path: Any) -> None:
    db_path = tmp_path / SESSION_DB_NAME
    SessionStore(db_path=db_path, session_key=KEY).login('alice')
    # simulate a schema bump: an older/newer version must discard the disposable rows
    raw = sqlite3.connect(str(db_path))
    raw.execute(f'PRAGMA user_version = {SESSION_DB_VERSION + 1}')
    raw.commit()
    raw.close()
    reopened = SessionStore(db_path=db_path, session_key=KEY)
    count = reopened._conn.execute('SELECT COUNT(*) FROM active_sessions').fetchone()[0]
    assert count == 0
