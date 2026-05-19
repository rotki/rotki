from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from rotkehlchen.mcp.backend import configure_backend
from rotkehlchen.mcp.constants import SERVICE_NAME, LogLevel
from rotkehlchen.mcp.registry import discover_tools


def setup_server(backend_url: str, timeout: int, log_level: LogLevel) -> FastMCP:
    configure_backend(base_url=backend_url, timeout=timeout)
    server = FastMCP(name=SERVICE_NAME, log_level=log_level)

    for tool_function in discover_tools():
        default_name = getattr(tool_function, '__name__', 'unknown')
        tool_name = getattr(tool_function, '__mcp_tool_name__', default_name)
        server.add_tool(
            tool_function,
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
