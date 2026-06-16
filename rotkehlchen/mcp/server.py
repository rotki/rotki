from __future__ import annotations

import asyncio
import functools
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

from rotkehlchen.mcp.backend import configure_backend
from rotkehlchen.mcp.constants import SERVICE_NAME, LogLevel
from rotkehlchen.mcp.premium import premium_gate
from rotkehlchen.mcp.registry import discover_tools

if TYPE_CHECKING:
    from collections.abc import Callable


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


def setup_server(backend_url: str, timeout: int, log_level: LogLevel) -> FastMCP:
    configure_backend(base_url=backend_url, timeout=timeout)
    server = FastMCP(name=SERVICE_NAME, log_level=log_level)

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


def run_server(backend_url: str, timeout: int, log_level: LogLevel) -> None:
    setup_server(
        backend_url=backend_url,
        timeout=timeout,
        log_level=log_level,
    ).run(transport='stdio')
