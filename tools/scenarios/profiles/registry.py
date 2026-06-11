"""Registry of available profiles"""
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Final

from tools.scenarios.profiles import empty, small, whale

if TYPE_CHECKING:
    from tools.scenarios.base import ProfileBuilder

PROFILES: Final[dict[str, Callable[['ProfileBuilder'], dict[str, Any] | None]]] = {
    'empty': empty.build,
    'small': small.build,
    'whale': whale.build,
}
