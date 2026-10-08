import importlib
import pkgutil
from contextlib import suppress
from functools import cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType


@cache
def discover_submodules(root: str, module_name: str) -> tuple[tuple[str, ModuleType], ...]:
    """Find every subpackage under `root` that has a `module_name` module and import it.

    The result is cached, so each process walks the filesystem and imports a given root once
    however many times a chain is constructed. That is safe because the cache holds the very
    module objects `sys.modules` already holds, and callers still look the classes up on them
    every time, so patching a decoder class is still honoured. What it would hide is a module
    that appears or disappears after the first call.

    Returns pairs of the subpackage path relative to `root`, with the dots left in, and its
    `module_name` module. The order is depth first, a package before its own subpackages, so
    rules built from it come out in the order they always did.
    """
    found: list[tuple[str, ModuleType]] = []
    package = importlib.import_module(root)
    for module_info in pkgutil.iter_modules(package.__path__):
        if module_info.ispkg is False:
            continue

        full_name = f'{package.__name__}.{module_info.name}'
        submodule = None
        with suppress(ModuleNotFoundError):
            submodule = importlib.import_module(f'{full_name}.{module_name}')

        if submodule is not None:
            found.append((full_name[len(root):], submodule))

        found.extend(
            (full_name[len(root):] + relative, module)
            for relative, module in discover_submodules(full_name, module_name)
        )

    return tuple(found)
