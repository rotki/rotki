"""Base repository class for database operations."""
from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


class BaseRepository(ABC):
    """Base class for all repository classes."""
    
    def __init__(self) -> None:
        """Initialize the base repository."""
        pass