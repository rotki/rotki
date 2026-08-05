"""Persistent authority for which session is live per user (Docker session cookie).

Generalises the old single ``active_session_id`` scalar into a per-user map, so the same
code enforces one live session per user for a single user today and many later. The
in-memory ``_active`` map is the hot authority; ``session.db`` (next to ``global.db``)
durably mirrors browser and MCP membership (``user``, ``sid``, ``mcp_sid``, ``abs``).
It stays quiet during a session except when rotating the MCP credential, which is what
lets colibri cache browser-session reads while MCP tokens remain immediately revocable.

``abs`` (the absolute ceiling) lives here, not in the token, so the token wire format and
colibri's validator are unchanged. ``session.db`` is disposable: its own
``PRAGMA user_version`` drops+recreates the table on mismatch rather than migrating, and
it is never wired into the user/global DB versioning.
"""
import secrets
import sqlite3
import time
from contextlib import closing
from threading import Semaphore
from typing import TYPE_CHECKING, Final, NamedTuple

from rotkehlchen.api.session_token import (
    SESSION_ABSOLUTE_TTL,
    SESSION_IDLE_TTL,
    mint_mcp_token,
    mint_session_token,
)

if TYPE_CHECKING:
    from pathlib import Path

SESSION_DB_NAME: Final = 'session.db'

# Bumping this drops and recreates the table on next open (sessions are disposable).
SESSION_DB_VERSION: Final = 2


class ActiveSession(NamedTuple):
    """The live session for a user. ``exp`` rolls forward on refresh but never past
    ``absolute_exp``; both are unix seconds."""
    sid: str
    absolute_exp: int
    exp: int
    mcp_sid: str | None


class SessionStore:
    """Authority for the currently-active session per user, mirrored to session.db."""

    def __init__(self, db_path: Path, session_key: bytes) -> None:
        self.session_key = session_key
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # shared across worker threads; the Semaphore serialises multi-step execute+commit
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._lock = Semaphore()
        # user -> ActiveSession; the hot authority (session.db is the durable mirror).
        self._active: dict[str, ActiveSession] = {}
        with self._lock:
            self._conn.execute('PRAGMA journal_mode=WAL')
            self._initialize_schema()
            self._load()

    def _initialize_schema(self) -> None:
        version = self._conn.execute('PRAGMA user_version').fetchone()[0]
        if version != SESSION_DB_VERSION:  # disposable: recreate rather than migrate
            self._conn.execute('DROP TABLE IF EXISTS active_sessions')
            self._conn.execute(f'PRAGMA user_version = {SESSION_DB_VERSION}')
        self._conn.execute(
            'CREATE TABLE IF NOT EXISTS active_sessions ('
            'user TEXT NOT NULL PRIMARY KEY, sid TEXT NOT NULL, '
            'mcp_sid TEXT, abs INTEGER NOT NULL)',
        )
        # Index on sid: colibri gates by sid membership, not by user.
        self._conn.execute(
            'CREATE INDEX IF NOT EXISTS idx_active_sessions_sid ON active_sessions(sid)',
        )
        self._conn.commit()

    def _load(self) -> None:
        """Rehydrate the in-memory map from session.db, pruning any past their ceiling.
        A restart resumes each session with a fresh idle window (still bounded by abs)."""
        current_time = int(time.time())
        self._conn.execute('DELETE FROM active_sessions WHERE abs <= ?', (current_time,))
        self._conn.commit()
        for user, sid, mcp_sid, absolute_exp in self._conn.execute(
            'SELECT user, sid, mcp_sid, abs FROM active_sessions',
        ):
            self._active[user] = ActiveSession(
                sid=sid,
                absolute_exp=absolute_exp,
                exp=min(current_time + SESSION_IDLE_TTL, absolute_exp),
                mcp_sid=mcp_sid,
            )

    def login(self, username: str) -> str:
        """Start (or take over) the active session for ``username`` and return its token.
        The UPSERT overwrites the user's prior session, so its old cookie is revoked, and
        every other user's row goes with it: core unlocks one user at a time, so a second
        row can only ever be a session that is no longer reachable. Leaving them behind is
        what let a previous user's cookie and MCP bearer outlive the login that displaced
        them, since the UPSERT alone only ever rewrites the row of the user logging in."""
        current_time = int(time.time())
        sid = secrets.token_hex(16)
        absolute_exp = current_time + SESSION_ABSOLUTE_TTL
        exp = min(current_time + SESSION_IDLE_TTL, absolute_exp)
        # Hold one lock over both the DB write and the in-memory update so concurrent
        # logins can't leave one sid in memory and a different one in the DB. Write the
        # DB first, so a failed commit never leaves memory ahead of the durable mirror.
        with self._lock:
            self._conn.execute('DELETE FROM active_sessions WHERE user != ?', (username,))
            self._conn.execute(
                'INSERT INTO active_sessions(user, sid, abs) VALUES(?, ?, ?) '
                'ON CONFLICT(user) DO UPDATE SET '
                'sid=excluded.sid, mcp_sid=NULL, abs=excluded.abs',
                (username, sid, absolute_exp),
            )
            self._conn.commit()
            for other in [user for user in self._active if user != username]:
                del self._active[other]
            self._active[username] = ActiveSession(
                sid=sid,
                absolute_exp=absolute_exp,
                exp=exp,
                mcp_sid=None,
            )
        return mint_session_token(self.session_key, username, sid, expires_at=exp)['token']

    def reissue(self, username: str, sid: str) -> str | None:
        """Rolling refresh: re-mint the *same* sid with a fresh idle ``exp`` capped at
        the session's absolute ceiling. Returns the new token, or ``None`` if this sid is
        not the user's active session (nothing to refresh). Never writes to the DB."""
        if (exp := self._refresh_exp(username=username, sid=sid)) is None:
            return None
        return mint_session_token(self.session_key, username, sid, expires_at=exp)['token']

    def _refresh_exp(self, username: str, sid: str) -> int | None:
        """Roll an active session's idle expiry and return it without minting a token."""
        with self._lock:  # same lock as the DB writers, so the read-modify-write is atomic
            active = self._active.get(username)
            if active is None or active.sid != sid:
                return None
            current_time = int(time.time())
            exp = min(current_time + SESSION_IDLE_TTL, active.absolute_exp)
            self._active[username] = active._replace(exp=exp)
        return exp

    def is_active(self, username: str, sid: str) -> bool:
        """Whether ``sid`` is the user's live session and within its absolute ceiling.
        The token's own ``exp`` (read_session_token) enforces the idle window."""
        active = self._active.get(username)
        if active is None or active.sid != sid:
            return False
        return int(time.time()) < active.absolute_exp

    def is_mcp_active(self, username: str, sid: str) -> bool:
        """Whether ``sid`` is the user's latest MCP credential."""
        active = self._active.get(username)
        if active is None or active.mcp_sid != sid:
            return False
        return int(time.time()) < active.absolute_exp

    def active_sid(self, username: str) -> str | None:
        """The sid of ``username``'s active session, or None. For test introspection."""
        active = self._active.get(username)
        return active.sid if active is not None else None

    def issue_mcp_token(self, username: str, sid: str) -> str | None:
        """Mint an MCP-only token linked to an authenticated active session.

        The token carries a freshly rotated MCP-only ``sid`` and uses a purpose-derived
        signing key, so it cannot authenticate as a browser cookie. Rotating the MCP
        ``sid``, logout, or session takeover revokes the prior bearer token. Its lifetime
        reaches the session's absolute ceiling without rolling the browser's idle expiry.
        """
        with self._lock:
            active = self._active.get(username)
            if (
                active is None or
                active.sid != sid or
                int(time.time()) >= active.absolute_exp
            ):
                return None
            mcp_sid = secrets.token_hex(16)
            self._conn.execute(
                'UPDATE active_sessions SET mcp_sid = ? WHERE user = ? AND sid = ?',
                (mcp_sid, username, sid),
            )
            self._conn.commit()
            self._active[username] = active._replace(mcp_sid=mcp_sid)
            return mint_mcp_token(
                key=self.session_key,
                username=username,
                sid=mcp_sid,
                expires_at=active.absolute_exp,
            )['token']

    def revoke(self, username: str) -> None:
        """Drop the active session for ``username`` (logout)."""
        with self._lock:
            self._conn.execute('DELETE FROM active_sessions WHERE user = ?', (username,))
            self._conn.commit()
            self._active.pop(username, None)

    def close(self) -> None:
        """Close the underlying connection (test cleanup; the process shares one store)."""
        with self._lock:
            self._conn.close()


def is_persisted_mcp_session_active(db_path: Path, username: str, sid: str) -> bool:
    """Check the durable MCP-session authority without mutating it.

    MCP runs in a separate process from core, so it cannot use the in-memory
    ``SessionStore``. Opening the disposable session database read-only makes logout
    and session takeover revoke bearer tokens without giving MCP write access.
    """
    try:
        with closing(
            sqlite3.connect(f'{db_path.resolve().as_uri()}?mode=ro', uri=True),
        ) as connection:
            row = connection.execute(
                'SELECT 1 FROM active_sessions WHERE user = ? AND mcp_sid = ? AND abs > ?',
                (username, sid, int(time.time())),
            ).fetchone()
    except sqlite3.Error:
        return False
    return row is not None
