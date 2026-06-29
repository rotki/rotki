from rotkehlchen.mcp import availability
from rotkehlchen.mcp.availability import MCP_UNAVAILABLE_REASON, get_mcp_server_info


def test_get_mcp_server_info_source(monkeypatch) -> None:
    monkeypatch.setattr(availability.sys, 'executable', '/usr/bin/python')
    monkeypatch.delattr(availability.sys, 'frozen', raising=False)
    monkeypatch.setattr(availability, '_has_mcp_package', lambda: True)

    result = get_mcp_server_info(backend_url=(backend_url := 'http://127.0.0.1:4242/api/1'))

    assert result == {
        'available': True,
        'command': '/usr/bin/python',
        'args': ['-m', 'rotkehlchen', 'mcp', '--backend-url', backend_url],
        'display_command': f'/usr/bin/python -m rotkehlchen mcp --backend-url {backend_url}',
    }


def test_get_mcp_server_info_packaged(monkeypatch) -> None:
    monkeypatch.setattr(availability.sys, 'executable', '/opt/rotki/rotki-core')
    monkeypatch.setattr(availability.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(availability, '_has_mcp_package', lambda: True)

    result = get_mcp_server_info(backend_url=(backend_url := 'http://127.0.0.1:4242/api/1'))

    assert result == {
        'available': True,
        'command': '/opt/rotki/rotki-core',
        'args': ['mcp', '--backend-url', backend_url],
        'display_command': f'/opt/rotki/rotki-core mcp --backend-url {backend_url}',
    }


def test_get_mcp_server_info_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(availability, '_has_mcp_package', lambda: False)

    assert get_mcp_server_info(backend_url='http://127.0.0.1:4242/api/1') == {
        'available': False,
        'reason': MCP_UNAVAILABLE_REASON,
    }
