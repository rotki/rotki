from __future__ import annotations

import asyncio
import functools
import logging
from ipaddress import ip_address
from typing import TYPE_CHECKING, Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from rotkehlchen.mcp.backend import configure_backend
from rotkehlchen.mcp.constants import SERVICE_NAME, LogLevel, PrivacyMode
from rotkehlchen.mcp.premium import premium_gate
from rotkehlchen.mcp.registry import discover_tools

if TYPE_CHECKING:
    from collections.abc import Callable


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
            'The unauthenticated streamable HTTP transport must bind to a loopback host',
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


def setup_server(
        backend_url: str,
        timeout: int,
        log_level: LogLevel,
        privacy_mode: PrivacyMode,
        max_events: int | None = None,
        host: str = '127.0.0.1',
        port: int = 4445,
) -> FastMCP:
    host = validate_loopback_host(host)
    configure_backend(
        base_url=backend_url,
        timeout=timeout,
        privacy_mode=privacy_mode,
        max_events=max_events,
    )
    http_host = _format_http_host(host=host, port=port)
    server = FastMCP(
        name=SERVICE_NAME,
        log_level=log_level,
        host=host,
        port=port,
        transport_security=TransportSecuritySettings(
            allowed_hosts=[http_host],
            allowed_origins=[f'http://{http_host}'],
        ),
    )

    for tool_function in discover_tools():
        default_name = getattr(tool_function, '__name__', 'unknown')
        tool_name = getattr(tool_function, '__mcp_tool_name__', default_name)
        server.add_tool(
            _gate_with_premium(tool_function)
            if getattr(tool_function, '__mcp_premium__', True) else tool_function,
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
    )
    server.run(transport=transport)
