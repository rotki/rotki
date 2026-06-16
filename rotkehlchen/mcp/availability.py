from __future__ import annotations

import shlex
import sys
from importlib.util import find_spec
from typing import Any, Final

MCP_UNAVAILABLE_REASON: Final = (
    'MCP server command is unavailable because the optional mcp dependency is not installed.'
)


def _format_display_command(command_parts: list[str]) -> str:
    return shlex.join(command_parts)


def _has_mcp_package() -> bool:
    return find_spec('mcp') is not None


def get_mcp_server_info(backend_url: str) -> dict[str, Any]:
    if _has_mcp_package() is False:
        return {
            'available': False,
            'reason': MCP_UNAVAILABLE_REASON,
        }

    args = [
        'mcp' if getattr(sys, 'frozen', False) else '-m',
        *([] if getattr(sys, 'frozen', False) else ['rotkehlchen', 'mcp']),
        '--backend-url',
        backend_url,
    ]
    command_parts = [sys.executable, *args]
    return {
        'available': True,
        'command': sys.executable,
        'args': args,
        'display_command': _format_display_command(command_parts),
    }
