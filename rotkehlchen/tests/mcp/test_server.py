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

    monkeypatch.setattr(server, 'discover_tools', lambda: [fake_tool])

    server.setup_server(
        backend_url='http://backend/api/1',
        timeout=3,
        log_level='DEBUG',
    )

    assert init_args == {'name': SERVICE_NAME, 'log_level': 'DEBUG'}
    assert tools == [('fake_tool', None, fake_tool)]
