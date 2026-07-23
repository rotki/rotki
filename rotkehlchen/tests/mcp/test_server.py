import asyncio
import logging
import selectors
from typing import Any
from unittest.mock import MagicMock

import pytest
from mcp.server.transport_security import TransportSecuritySettings

from rotkehlchen import __main__ as rotkehlchen_main
from rotkehlchen.mcp import __main__ as mcp_main, server
from rotkehlchen.mcp.constants import SERVICE_NAME


def test_setup_server_should_register_discovered_tools(monkeypatch) -> None:
    tools = []
    init_args: dict[str, object] = {}

    class MockFastMCP:
        def __init__(
                self,
                name: str,
                log_level: str,
                host: str,
                port: int,
                transport_security: TransportSecuritySettings,
        ) -> None:
            init_args['name'] = name
            init_args['log_level'] = log_level
            init_args['host'] = host
            init_args['port'] = port
            init_args['transport_security'] = transport_security

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

    assert init_args['name'] == SERVICE_NAME
    assert init_args['log_level'] == 'DEBUG'
    assert init_args['host'] == '127.0.0.1'
    assert init_args['port'] == 4445
    assert isinstance(
        transport_security := init_args['transport_security'],
        TransportSecuritySettings,
    )
    assert transport_security.enable_dns_rebinding_protection is True
    assert transport_security.allowed_hosts == ['127.0.0.1:4445']
    assert transport_security.allowed_origins == ['http://127.0.0.1:4445']
    assert tools == [('fake_tool', None, fake_tool)]


def test_setup_server_should_gate_premium_tools(monkeypatch) -> None:
    """A premium-gated tool is wrapped so it can't run without an active subscription."""
    tools = []

    class MockFastMCP:
        def __init__(
                self,
                name: str,
                log_level: str,
                host: str,
                port: int,
                transport_security: TransportSecuritySettings,
        ) -> None:
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


def test_run_server_should_use_stdio_transport(monkeypatch) -> None:
    server_mock = MagicMock()
    monkeypatch.setattr(server, 'setup_server', MagicMock(return_value=server_mock))

    server.run_server(
        backend_url='http://127.0.0.1:4242/api/1',
        timeout=5,
        log_level='INFO',
        privacy_mode='balanced',
    )

    server_mock.run.assert_called_once_with(transport='stdio')


def test_main_should_forward_cli_arguments(monkeypatch) -> None:
    run_server_mock = MagicMock()
    monkeypatch.setattr(mcp_main, 'run_server', run_server_mock)

    mcp_main.main([
        '--backend-url', 'http://127.0.0.1:4243/api/1',
        '--host', '127.0.0.2',
        '--log-level', 'DEBUG',
        '--max-events', '42',
        '--port', '4450',
        '--privacy-mode', 'strict',
        '--timeout', '10',
        '--transport', 'streamable-http',
    ])

    run_server_mock.assert_called_once_with(
        backend_url='http://127.0.0.1:4243/api/1',
        host='127.0.0.2',
        log_level='DEBUG',
        max_events=42,
        port=4450,
        privacy_mode='strict',
        timeout=10,
        transport='streamable-http',
    )


@pytest.mark.parametrize('host', ['127.0.0.1', '127.1.2.3', '::1', 'localhost'])
def test_validate_loopback_host_should_allow_only_loopback(host: str) -> None:
    assert server.validate_loopback_host(host) == host


@pytest.mark.parametrize('host', ['0.0.0.0', '192.168.1.2', 'example.com'])  # noqa: S104
def test_validate_loopback_host_should_reject_network_exposure(host: str) -> None:
    with pytest.raises(ValueError, match='must bind to a loopback host'):
        server.validate_loopback_host(host)


def test_main_should_reject_non_loopback_http_host(monkeypatch) -> None:
    run_server_mock = MagicMock()
    monkeypatch.setattr(mcp_main, 'run_server', run_server_mock)

    with pytest.raises(SystemExit) as error:
        mcp_main.main(['--transport', 'streamable-http', '--host', '0.0.0.0'])  # noqa: S104

    assert error.value.code == 2
    run_server_mock.assert_not_called()


def test_rotkehlchen_main_should_report_mcp_startup_errors(monkeypatch, capsys) -> None:
    monkeypatch.setattr(rotkehlchen_main, 'is_mcp_command', True)
    monkeypatch.setattr(
        rotkehlchen_main,
        'mcp_main',
        MagicMock(side_effect=OSError('address already in use')),
        raising=False,
    )

    with pytest.raises(SystemExit) as error:
        rotkehlchen_main.main()

    assert error.value.code == 1
    assert capsys.readouterr().err.endswith(
        'Failed to start rotki MCP server: address already in use\n',
    )


def test_rotkehlchen_main_should_dispatch_mcp_arguments(monkeypatch) -> None:
    mcp_main_mock = MagicMock()
    monkeypatch.setattr(rotkehlchen_main, 'is_mcp_command', True)
    monkeypatch.setattr(rotkehlchen_main, 'mcp_main', mcp_main_mock, raising=False)
    monkeypatch.setattr(
        rotkehlchen_main.sys,
        'argv',
        ['rotkehlchen', 'mcp', '--transport', 'stdio'],
    )

    rotkehlchen_main.main()

    mcp_main_mock.assert_called_once_with(['--transport', 'stdio'])
