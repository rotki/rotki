from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

AVAILABLE_TOOLS: list[Callable[..., Any]] = []


def register_tool(
        fn: Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        premium: bool = True,
) -> Callable[..., Any]:
    """Register a decorated function as an MCP tool.

    Tools require an active premium subscription by default. Pass ``premium=False`` for
    tools that must stay available to everyone (e.g. ``info``), so a new tool can never
    leak data for free by forgetting to opt in.
    """
    def _decorate(function: Callable[..., Any]) -> Callable[..., Any]:
        function.__mcp_tool_name__ = name or function.__name__  # type: ignore[attr-defined]
        function.__mcp_premium__ = premium  # type: ignore[attr-defined]
        AVAILABLE_TOOLS.append(function)
        return function

    if fn is None:
        return _decorate

    return _decorate(fn)


def discover_tools() -> list[Callable[..., Any]]:
    """Import all tool modules so that @register_tool decorators run."""
    import importlib
    import pkgutil

    package_name = 'rotkehlchen.mcp.tools'
    package = importlib.import_module(package_name)

    for module_info in pkgutil.walk_packages(package.__path__, package_name + '.'):
        if module_info.name.rsplit('.', 1)[-1].startswith('_'):
            continue
        importlib.import_module(module_info.name)

    return sorted(
        AVAILABLE_TOOLS,
        key=lambda tool: getattr(tool, '__mcp_tool_name__', tool.__name__),
    )
