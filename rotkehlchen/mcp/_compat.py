import importlib
import importlib.util
import sys
from types import ModuleType
from typing import Final

_MCP_WIN32_CLIENT_MODULES: Final = ('pywintypes', 'win32api', 'win32con', 'win32job')


def prepare_mcp_server() -> None:
    """Load MCP's server modules when pywin32 is unavailable on free-threaded Python.

    MCP 1.x eagerly imports its Windows stdio client from the package initializer,
    although rotki only runs its HTTP server. pywin32 has no cp314t wheel. Supply
    temporary import placeholders, then disable the unused client integration in
    MCP's already-loaded Windows utility module.
    """
    placeholders = {
        module_name: ModuleType(module_name)
        for module_name in _MCP_WIN32_CLIENT_MODULES
    }
    sys.modules.update(placeholders)
    try:
        importlib.import_module('mcp')
        win32_utilities = sys.modules['mcp.os.win32.utilities']
        for module_name in _MCP_WIN32_CLIENT_MODULES:
            setattr(win32_utilities, module_name, None)
    finally:
        for module_name, placeholder in placeholders.items():
            if sys.modules.get(module_name) is placeholder:
                del sys.modules[module_name]


if sys.platform == 'win32' and importlib.util.find_spec('pywintypes') is None:
    prepare_mcp_server()
