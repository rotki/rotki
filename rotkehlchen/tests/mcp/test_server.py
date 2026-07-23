import asyncio
import logging
import selectors
from typing import Any

from rotkehlchen.mcp import server
from rotkehlchen.mcp.constants import SERVICE_NAME


def test_setup_server_should_register_discovered_tools(monkeypatch) -> None:
    tools = []
    init_args: dict[str, object] = {}

    class MockFastMCP:
        def __init__(self, name: str, log_level: str, host: str, port: int) -> None:
            init_args['name'] = name
            init_args['log_level'] = log_level
            init_args['host'] = host
            init_args['port'] = port

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
        privacy_mode='balanced',
    )

    assert init_args == {
        'name': SERVICE_NAME,
        'log_level': 'DEBUG',
        'host': '127.0.0.1',
        'port': 4445,
    }
    assert tools == [('fake_tool', None, fake_tool)]


def test_setup_server_should_gate_premium_tools(monkeypatch) -> None:
    """A premium-gated tool is wrapped so it can't run without an active subscription."""
    tools = []

    class MockFastMCP:
        def __init__(self, name: str, log_level: str, host: str, port: int) -> None:
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
    server.setup_server(
        backend_url='http://backend/api/1',
        timeout=3,
        log_level='DEBUG',
        privacy_mode='balanced',
    )

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


def test_run_server_should_use_streamable_http_transport(monkeypatch) -> None:
    setup_kwargs = {}
    transports = []

    class MockServer:
        def run(self, transport: str) -> None:
            transports.append(transport)

    def mock_setup_server(**kwargs: Any) -> MockServer:
        setup_kwargs.update(kwargs)
        return MockServer()

    monkeypatch.setattr(server, 'setup_server', mock_setup_server)

    sse_logger = logging.getLogger('sse_starlette.sse')
    previous_level = sse_logger.level
    try:
        server.run_server(
            backend_url='http://127.0.0.1:4242/api/1',
            timeout=5,
            log_level='INFO',
            privacy_mode='balanced',
            transport='streamable-http',
            host='127.0.0.1',
            port=4445,
        )
        assert sse_logger.level == logging.INFO
    finally:
        sse_logger.setLevel(previous_level)

    assert setup_kwargs['host'] == '127.0.0.1'
    assert setup_kwargs['port'] == 4445
    assert transports == ['streamable-http']
