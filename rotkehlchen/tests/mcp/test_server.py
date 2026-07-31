import asyncio
import logging
import selectors
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings
from starlette.testclient import TestClient

from rotkehlchen import __main__ as rotkehlchen_main
from rotkehlchen.api.session_store import SessionStore
from rotkehlchen.api.session_token import read_session_token
from rotkehlchen.mcp import __main__ as mcp_main, server
from rotkehlchen.mcp.auth import MCP_SCOPE, SessionTokenVerifier
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
                auth: Any,
                token_verifier: Any,
                transport_security: TransportSecuritySettings,
        ) -> None:
            init_args['name'] = name
            init_args['log_level'] = log_level
            init_args['host'] = host
            init_args['port'] = port
            init_args['auth'] = auth
            init_args['token_verifier'] = token_verifier
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
    assert init_args['auth'] is None
    assert init_args['token_verifier'] is None
    assert isinstance(
        transport_security := init_args['transport_security'],
        TransportSecuritySettings,
    )
    assert transport_security.enable_dns_rebinding_protection is True
    assert transport_security.allowed_hosts == ['127.0.0.1:4445']
    assert transport_security.allowed_origins == ['http://127.0.0.1:4445']
    assert len(tools) == 1
    assert tools[0][:2] == ('fake_tool', None)
    assert tools[0][2] is not fake_tool


def test_setup_server_should_enable_bearer_authentication(monkeypatch, tmp_path: Path) -> None:
    init_args: dict[str, object] = {}

    class MockFastMCP:
        def __init__(self, **kwargs: Any) -> None:
            init_args.update(kwargs)

        def add_tool(self, fn: Any, name: str, description: str | None = None) -> None:
            pass

    monkeypatch.setattr(server, 'FastMCP', MockFastMCP)
    monkeypatch.setattr(server, 'discover_tools', list)

    server.setup_server(
        backend_url='http://backend/api/1',
        timeout=3,
        log_level='INFO',
        privacy_mode='balanced',
        session_key=b'session-key',
        session_db=(session_db := tmp_path / 'session.db'),
    )

    assert isinstance(auth := init_args['auth'], AuthSettings)
    assert str(auth.issuer_url) == 'http://backend/api/1'
    assert auth.required_scopes == [MCP_SCOPE]
    assert isinstance(token_verifier := init_args['token_verifier'], SessionTokenVerifier)
    assert token_verifier.session_db == session_db


def test_streamable_http_should_authenticate_before_protocol_handling(
        monkeypatch,
        tmp_path: Path,
) -> None:
    session_db = tmp_path / 'session.db'
    store = SessionStore(db_path=session_db, session_key=(session_key := b'session-key'))

    def authenticated_subject() -> str:
        access_token = get_access_token()
        return access_token.subject if access_token is not None and access_token.subject is not None else 'missing'  # noqa: E501

    authenticated_subject.__mcp_premium__ = False  # type: ignore[attr-defined]
    monkeypatch.setattr(server, 'discover_tools', lambda: [authenticated_subject])
    mcp_server = server.setup_server(
        backend_url='http://backend/api/1',
        timeout=3,
        log_level='INFO',
        privacy_mode='balanced',
        session_key=session_key,
        session_db=session_db,
    )
    request = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'initialize',
        'params': {
            'protocolVersion': '2025-06-18',
            'capabilities': {},
            'clientInfo': {'name': 'test-client', 'version': '1.0'},
        },
    }
    headers = {'Accept': 'application/json, text/event-stream'}
    try:
        with TestClient(
            mcp_server.streamable_http_app(),
            base_url='http://127.0.0.1:4445',
        ) as client:
            unauthorized = client.post('/mcp', json=request, headers=headers)
            assert unauthorized.status_code == 401

            malformed = client.post(
                '/mcp',
                json=request,
                headers=[
                    (b'Accept', b'application/json, text/event-stream'),
                    (b'Authorization', b'Bearer truncated-\xe2\x80\xa6.token'),
                ],
            )
            assert malformed.status_code == 401

            session_token = store.login('alice')
            session_headers = {**headers, 'Authorization': f'Bearer {session_token}'}
            assert client.post('/mcp', json=request, headers=session_headers).status_code == 401

            assert (claims := read_session_token(session_key, session_token)) is not None
            token = store.issue_mcp_token('alice', claims.sid)
            assert token is not None
            authorized_headers = {**headers, 'Authorization': f'Bearer {token}'}
            authorized = client.post(
                '/mcp',
                json=request,
                headers=authorized_headers,
            )
            assert authorized.status_code == 200
            assert f'"name":"{SERVICE_NAME}"' in authorized.text

            authorized_headers['mcp-session-id'] = authorized.headers['mcp-session-id']
            initialized = client.post(
                '/mcp',
                json={'jsonrpc': '2.0', 'method': 'notifications/initialized'},
                headers=authorized_headers,
            )
            assert initialized.status_code == 202

            tool_call = client.post(
                '/mcp',
                json={
                    'jsonrpc': '2.0',
                    'id': 2,
                    'method': 'tools/call',
                    'params': {'name': 'authenticated_subject', 'arguments': {}},
                },
                headers=authorized_headers,
            )
            assert tool_call.status_code == 200
            assert '"text":"alice"' in tool_call.text
    finally:
        store.close()


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
                auth: Any,
                token_verifier: Any,
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

    name, description, registered_tool = tools[0]
    assert name == 'gated_tool'
    assert description == 'A gated tool.'  # docstring preserved through the wrapper
    assert registered_tool is not gated_tool
    wrapped = server._gate_with_premium(gated_tool)

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
    assert setup_kwargs['session_key'] is None
    assert setup_kwargs['session_db'] is None
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
    monkeypatch.setenv('ROTKI_SESSION_KEY', 'session-key')

    mcp_main.main([
        '--backend-url', 'http://127.0.0.1:4243/api/1',
        '--host', '127.0.0.2',
        '--log-level', 'DEBUG',
        '--max-events', '42',
        '--port', '4450',
        '--privacy-mode', 'strict',
        '--session-db', '/data/global/session.db',
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
        session_db=Path('/data/global/session.db'),
        session_key=b'session-key',
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
    monkeypatch.setattr(mcp_main, 'main', MagicMock(side_effect=OSError('address already in use')))

    with pytest.raises(SystemExit) as error:
        rotkehlchen_main.main()

    assert error.value.code == 1
    assert capsys.readouterr().err.endswith(
        'Failed to start rotki MCP server: address already in use\n',
    )


def test_rotkehlchen_main_should_report_mcp_server_exit(monkeypatch, capsys) -> None:
    monkeypatch.setattr(rotkehlchen_main, 'is_mcp_command', True)
    monkeypatch.setattr(mcp_main, 'main', MagicMock(side_effect=SystemExit(1)))

    with pytest.raises(SystemExit) as error:
        rotkehlchen_main.main()

    assert error.value.code == 1
    assert capsys.readouterr().err.endswith('Failed to start rotki MCP server\n')


def test_rotkehlchen_main_should_preserve_mcp_argument_errors(monkeypatch, capsys) -> None:
    monkeypatch.setattr(rotkehlchen_main, 'is_mcp_command', True)
    monkeypatch.setattr(mcp_main, 'main', MagicMock(side_effect=SystemExit(2)))

    with pytest.raises(SystemExit) as error:
        rotkehlchen_main.main()

    assert error.value.code == 2
    assert 'Failed to start rotki MCP server' not in capsys.readouterr().err


def test_rotkehlchen_main_should_dispatch_mcp_arguments(monkeypatch) -> None:
    mcp_main_mock = MagicMock()
    monkeypatch.setattr(rotkehlchen_main, 'is_mcp_command', True)
    monkeypatch.setattr(mcp_main, 'main', mcp_main_mock)
    monkeypatch.setattr(
        rotkehlchen_main.sys,
        'argv',
        ['rotkehlchen', 'mcp', '--transport', 'stdio'],
    )

    rotkehlchen_main.main()

    mcp_main_mock.assert_called_once_with(['--transport', 'stdio'])
