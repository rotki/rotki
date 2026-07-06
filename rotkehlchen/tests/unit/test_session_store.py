"""Unit tests for the persistent single-active-session store (Docker cookie auth)."""
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest
from freezegun import freeze_time

from rotkehlchen.api.session_store import (
    SESSION_DB_NAME,
    SESSION_DB_VERSION,
    SessionStore,
)
from rotkehlchen.api.session_token import (
    SESSION_ABSOLUTE_TTL,
    SESSION_IDLE_TTL,
    read_session_token,
)

KEY = b'unit-test-session-key'
# 2023-11-14 22:13:20 UTC == 1_700_000_000 unix seconds
BASE = datetime(2023, 11, 14, 22, 13, 20, tzinfo=UTC)
BASE_TS = int(BASE.timestamp())


def _store(tmp_path) -> SessionStore:
    return SessionStore(db_path=tmp_path / SESSION_DB_NAME, session_key=KEY)


@pytest.mark.freeze_time(BASE)
def test_login_mints_active_token(tmp_path):
    store = _store(tmp_path)
    token = store.login('alice')
    claims = read_session_token(KEY, token)
    assert claims is not None
    assert claims.username == 'alice'
    assert claims.exp == BASE_TS + SESSION_IDLE_TTL  # rolling idle window, not the 7d default
    assert store.is_active('alice', claims.sid) is True


@pytest.mark.freeze_time(BASE)
def test_new_login_kicks_previous_session(tmp_path):
    store = _store(tmp_path)
    first = read_session_token(KEY, store.login('alice'))
    second = read_session_token(KEY, store.login('alice'))
    assert first is not None and second is not None
    assert first.sid != second.sid
    # takeover: only the newest sid is active; the previous cookie is revoked
    assert store.is_active('alice', first.sid) is False
    assert store.is_active('alice', second.sid) is True


@pytest.mark.freeze_time(BASE)
def test_is_active_rejects_unknown_user_and_wrong_sid(tmp_path):
    store = _store(tmp_path)
    claims = read_session_token(KEY, store.login('alice'))
    assert claims is not None
    assert store.is_active('bob', claims.sid) is False  # no session for bob
    assert store.is_active('alice', 'deadbeef') is False  # wrong sid


@pytest.mark.freeze_time(BASE)
def test_login_is_per_user_isolated(tmp_path):
    store = _store(tmp_path)
    alice = read_session_token(KEY, store.login('alice'))
    bob = read_session_token(KEY, store.login('bob'))
    assert alice is not None and bob is not None
    # bob logging in does not disturb alice's session (per-user single-active)
    assert store.is_active('alice', alice.sid) is True
    assert store.is_active('bob', bob.sid) is True


def test_reissue_rolls_exp_and_caps_at_absolute(tmp_path):
    with freeze_time(BASE):
        store = _store(tmp_path)
        claims = read_session_token(KEY, store.login('alice'))
        assert claims is not None
    # a later request rolls the idle window forward
    later_ts = BASE_TS + SESSION_IDLE_TTL // 2
    with freeze_time(BASE + timedelta(seconds=SESSION_IDLE_TTL // 2)):
        rolled = read_session_token(KEY, store.reissue('alice', claims.sid))
        assert rolled is not None
        assert rolled.sid == claims.sid  # same session, not a takeover
        assert rolled.exp == later_ts + SESSION_IDLE_TTL
    # near the absolute ceiling, the rolled exp is capped at abs, never beyond
    with freeze_time(BASE + timedelta(seconds=SESSION_ABSOLUTE_TTL - 10)):
        capped = read_session_token(KEY, store.reissue('alice', claims.sid))
        assert capped is not None
        assert capped.exp == BASE_TS + SESSION_ABSOLUTE_TTL


@pytest.mark.freeze_time(BASE)
def test_reissue_rejects_non_active_sid(tmp_path):
    store = _store(tmp_path)
    store.login('alice')
    assert store.reissue('alice', 'not-the-active-sid') is None
    assert store.reissue('nobody', 'whatever') is None


@pytest.mark.freeze_time(BASE)
def test_revoke_removes_session(tmp_path):
    store = _store(tmp_path)
    claims = read_session_token(KEY, store.login('alice'))
    assert claims is not None
    store.revoke('alice')
    assert store.is_active('alice', claims.sid) is False


def test_session_survives_restart(tmp_path):
    db_path = tmp_path / SESSION_DB_NAME
    with freeze_time(BASE):
        claims = read_session_token(KEY, SessionStore(db_path=db_path, session_key=KEY).login('alice'))  # noqa: E501
        assert claims is not None
        # a fresh store on the same file rehydrates the active session from session.db
        reopened = SessionStore(db_path=db_path, session_key=KEY)
        assert reopened.is_active('alice', claims.sid) is True


def test_expired_sessions_pruned_on_load(tmp_path):
    db_path = tmp_path / SESSION_DB_NAME
    with freeze_time(BASE):
        claims = read_session_token(KEY, SessionStore(db_path=db_path, session_key=KEY).login('alice'))  # noqa: E501
        assert claims is not None
    # reopen well past the absolute ceiling: the row is pruned, session gone
    with freeze_time(BASE + timedelta(seconds=SESSION_ABSOLUTE_TTL + 1)):
        reopened = SessionStore(db_path=db_path, session_key=KEY)
        assert reopened.is_active('alice', claims.sid) is False


@pytest.mark.freeze_time(BASE)
def test_version_mismatch_recreates_table(tmp_path):
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
