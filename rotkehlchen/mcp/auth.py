"""Bearer-token authentication for the streamable HTTP MCP transport."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Final

from mcp.server.auth.provider import AccessToken

from rotkehlchen.api.session_store import is_persisted_session_active
from rotkehlchen.api.session_token import read_mcp_token

if TYPE_CHECKING:
    from pathlib import Path

MCP_SCOPE: Final = 'mcp'


class SessionTokenVerifier:  # pylint: disable=too-few-public-methods
    """Validate backend-issued bearer tokens against the active Docker session."""

    def __init__(self, session_key: bytes, session_db: Path) -> None:
        self.session_key = session_key
        self.session_db = session_db

    async def verify_token(self, token: str) -> AccessToken | None:
        """Return MCP access claims only for a signed, currently active session."""
        if (claims := read_mcp_token(self.session_key, token)) is None:
            return None
        if not await asyncio.to_thread(
            is_persisted_session_active,
            self.session_db,
            claims.username,
            claims.sid,
        ):
            return None
        return AccessToken(
            token=token,
            client_id='rotki-backend',
            scopes=[MCP_SCOPE],
            expires_at=claims.exp,
            subject=claims.username,
        )
