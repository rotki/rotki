from __future__ import annotations

import asyncio
import functools
import inspect
import logging
from ipaddress import ip_address
from typing import TYPE_CHECKING, Any, Literal

from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl

from rotkehlchen.mcp.auth import MCP_SCOPE, SessionTokenVerifier
from rotkehlchen.mcp.backend import configure_backend
from rotkehlchen.mcp.constants import SERVICE_NAME, LogLevel, PrivacyMode
from rotkehlchen.mcp.premium import premium_gate
from rotkehlchen.mcp.registry import discover_tools
from rotkehlchen.mcp.usage_analytics import (
    McpUsageAnalyticsTracker,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def validate_loopback_host(host: str) -> str:
    """Return host if it is an explicit loopback address, otherwise reject it."""
    if host == 'localhost':
        return host

    try:
        is_loopback = ip_address(host).is_loopback
    except ValueError:
        is_loopback = False

    if not is_loopback:
        raise ValueError(
            'The MCP streamable HTTP transport must bind to a loopback host',
        )
    return host


def _format_http_host(host: str, port: int) -> str:
    """Format a validated host for HTTP Host and Origin allowlists."""
    return f'[{host}]:{port}' if ':' in host else f'{host}:{port}'


def _gate_with_premium(tool_function: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap a tool so it returns a structured error unless the backend has premium.

    ``functools.wraps`` keeps the original signature and docstring so FastMCP still
    derives the correct input schema from the wrapped tool.
    """
    @functools.wraps(tool_function)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        if (error := await asyncio.to_thread(premium_gate)) is not None:
            return error
        return await tool_function(*args, **kwargs)

    return wrapper


def _track_usage_analytics(
        server: FastMCP,
        tracker: McpUsageAnalyticsTracker,
        tool_function: Callable[..., Any],
) -> Callable[..., Any]:
    """Submit client/model analytics at most once for each MCP session and model."""
    @functools.wraps(tool_function)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        request_context = server.get_context().request_context
        if (client_params := request_context.session.client_params) is not None:
            tracker.track(
                session=request_context.session,
                client_params=client_params,
                request_meta=request_context.meta,
            )

        result = tool_function(*args, **kwargs)
        return await result if inspect.isawaitable(result) else result

    return wrapper


def setup_server(
        backend_url: str,
        timeout: int,
        log_level: LogLevel,
        privacy_mode: PrivacyMode,
        max_events: int | None = None,
        host: str = '127.0.0.1',
        port: int = 4445,
        session_key: bytes | None = None,
        session_db: Path | None = None,
) -> FastMCP:
    host = validate_loopback_host(host)
    if session_key is not None and session_db is None:
        raise ValueError(
            'The session database path is required when MCP authentication is enabled',
        )
    configure_backend(
        base_url=backend_url,
        timeout=timeout,
        session_key=session_key,
        privacy_mode=privacy_mode,
        max_events=max_events,
    )
    http_host = _format_http_host(host=host, port=port)
    server = FastMCP(
        name=SERVICE_NAME,
        log_level=log_level,
        host=host,
        port=port,
        auth=AuthSettings(
            issuer_url=AnyHttpUrl(backend_url),
            required_scopes=[MCP_SCOPE],
            resource_server_url=None,
        ) if session_key is not None else None,
        token_verifier=SessionTokenVerifier(session_key=session_key, session_db=session_db)
        if session_key is not None and session_db is not None else None,
        transport_security=TransportSecuritySettings(
            allowed_hosts=[http_host],
            allowed_origins=[f'http://{http_host}'],
        ),
    )

    usage_analytics = McpUsageAnalyticsTracker()
    for tool_function in discover_tools():
        default_name = getattr(tool_function, '__name__', 'unknown')
        tool_name = getattr(tool_function, '__mcp_tool_name__', default_name)
        registered_function = (
            _gate_with_premium(tool_function)
            if getattr(tool_function, '__mcp_premium__', True) else tool_function
        )
        server.add_tool(
            _track_usage_analytics(
                server=server,
                tracker=usage_analytics,
                tool_function=registered_function,
            ),
            name=tool_name,
            description=tool_function.__doc__,
        )

    return server


def run_server(
        backend_url: str,
        timeout: int,
        log_level: LogLevel,
        privacy_mode: PrivacyMode,
        max_events: int | None = None,
        transport: Literal['stdio', 'streamable-http'] = 'stdio',
        host: str = '127.0.0.1',
        port: int = 4445,
        session_key: bytes | None = None,
        session_db: Path | None = None,
) -> None:
    if transport == 'streamable-http':
        # sse-starlette logs every serialized SSE payload (and ping body) at DEBUG.
        # Keep MCP debug logs useful without leaking protocol payloads into Electron logs.
        logging.getLogger('sse_starlette.sse').setLevel(logging.INFO)

    server = setup_server(
        backend_url=backend_url,
        timeout=timeout,
        log_level=log_level,
        privacy_mode=privacy_mode,
        max_events=max_events,
        host=host,
        port=port,
        session_key=session_key if transport == 'streamable-http' else None,
        session_db=session_db if transport == 'streamable-http' else None,
    )
    server.run(transport=transport)
