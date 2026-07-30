import asyncio
from typing import TYPE_CHECKING

from rotkehlchen.api.session_store import SessionStore
from rotkehlchen.api.session_token import read_session_token
from rotkehlchen.mcp.auth import MCP_SCOPE, SessionTokenVerifier

if TYPE_CHECKING:
    from pathlib import Path


def test_session_token_verifier_should_require_active_session(tmp_path: Path) -> None:
    session_db = tmp_path / 'session.db'
    store = SessionStore(db_path=session_db, session_key=(session_key := b'test-key'))
    session_token = store.login(username := 'alice')
    assert (claims := read_session_token(session_key, session_token)) is not None
    token = store.issue_mcp_token(username=username, sid=claims.sid)
    assert token is not None
    verifier = SessionTokenVerifier(session_key=session_key, session_db=session_db)
    try:
        access_token = asyncio.run(verifier.verify_token(token))
        assert access_token is not None
        assert access_token.token == token
        assert access_token.scopes == [MCP_SCOPE]
        assert access_token.subject == username

        replacement_token = store.issue_mcp_token(username=username, sid=claims.sid)
        assert replacement_token is not None
        assert asyncio.run(verifier.verify_token(token)) is None
        assert asyncio.run(verifier.verify_token(replacement_token)) is not None

        store.revoke(username)
        assert asyncio.run(verifier.verify_token(replacement_token)) is None
    finally:
        store.close()


def test_session_token_verifier_should_reject_invalid_token(tmp_path: Path) -> None:
    verifier = SessionTokenVerifier(
        session_key=b'test-key',
        session_db=tmp_path / 'missing-session.db',
    )

    assert asyncio.run(verifier.verify_token('not-a-token')) is None
