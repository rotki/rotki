from enum import Enum, auto
from typing import NamedTuple


class UpdateFileType(Enum):
    ASSETS = auto()
    ASSET_COLLECTIONS = auto()
    ASSET_COLLECTIONS_MAPPINGS = auto()


class VersionRange(NamedTuple):
    """Represents a version range with inclusive bounds"""
    start: int
    end: int | None = None  # None means no upper bound

    def contains(self, version: int) -> bool:
        """Check if a version is within this range"""
        if self.end is None:
            return version >= self.start

        return self.start <= version <= self.end
