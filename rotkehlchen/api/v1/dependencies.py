"""FastAPI dependencies for v1 API endpoints"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen

# This will be set by the ASGI server
_rotkehlchen_instance: 'Rotkehlchen | None' = None


def set_rotkehlchen_instance(rotkehlchen: 'Rotkehlchen') -> None:
    """Set the global Rotkehlchen instance for dependency injection"""
    global _rotkehlchen_instance
    _rotkehlchen_instance = rotkehlchen


async def get_rotkehlchen() -> 'Rotkehlchen':
    """Get Rotkehlchen instance for dependency injection"""
    if _rotkehlchen_instance is None:
        raise RuntimeError("Rotkehlchen instance not configured")
    return _rotkehlchen_instance