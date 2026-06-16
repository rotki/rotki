import asyncio
import selectors
from typing import Any

from rotkehlchen.mcp import server
from rotkehlchen.mcp.constants import SERVICE_NAME


def test_setup_server_should_register_discovered_tools(monkeypatch) -> None:
    tools = []
    init_args = {}

    class MockFastMCP:
        def __init__(self, name: str, log_level: str) -> None:
            init_args['name'] = name
            init_args['log_level'] = log_level

        def add_tool(
                self,
                fn: Any,
                name: str,
                description: str | None = None,
        ) -> None:
            tools.append((name, description, fn))

    monkeypatch.setattr(server, 'FastMCP', MockFastMCP)

    def fake_tool() -> dict[str, Any]:
        return {'result': 'ok'}

    fake_tool.__mcp_tool_name__ = 'fake_tool'  # type: ignore[attr-defined]
    fake_tool.__mcp_premium__ = False  # type: ignore[attr-defined]

    monkeypatch.setattr(server, 'discover_tools', lambda: [fake_tool])

    server.setup_server(
        backend_url='http://backend/api/1',
        timeout=3,
        log_level='DEBUG',
    )

    assert init_args == {'name': SERVICE_NAME, 'log_level': 'DEBUG'}
    assert tools == [('fake_tool', None, fake_tool)]


def test_setup_server_should_gate_premium_tools(monkeypatch) -> None:
    """A premium-gated tool is wrapped so it can't run without an active subscription."""
    tools = []

    class MockFastMCP:
        def __init__(self, name: str, log_level: str) -> None:
            pass

        def add_tool(self, fn: Any, name: str, description: str | None = None) -> None:
            tools.append((name, description, fn))

    monkeypatch.setattr(server, 'FastMCP', MockFastMCP)

    calls = []

    async def gated_tool() -> dict[str, Any]:  # noqa: RUF029  -- mimics an async MCP tool
        """A gated tool."""
        calls.append('ran')
        return {'result': 'ok'}

    gated_tool.__mcp_tool_name__ = 'gated_tool'  # type: ignore[attr-defined]
    gated_tool.__mcp_premium__ = True  # type: ignore[attr-defined]

    monkeypatch.setattr(server, 'discover_tools', lambda: [gated_tool])
    server.setup_server(backend_url='http://backend/api/1', timeout=3, log_level='DEBUG')

    name, description, wrapped = tools[0]
    assert name == 'gated_tool'
    assert description == 'A gated tool.'  # docstring preserved through the wrapper
    assert wrapped is not gated_tool  # the gated tool got wrapped

    loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
    try:
        # backend reports no premium -> wrapper short-circuits with an error
        monkeypatch.setattr(server, 'premium_gate', lambda: {'error': 'premium_required'})
        assert loop.run_until_complete(wrapped()) == {'error': 'premium_required'}
        assert calls == []  # the underlying tool never ran

        # backend reports premium -> wrapper delegates to the real tool
        monkeypatch.setattr(server, 'premium_gate', lambda: None)
        assert loop.run_until_complete(wrapped()) == {'result': 'ok'}
        assert calls == ['ran']
    finally:
        loop.close()
