import collections
from typing import Generic, Optional, OrderedDict, TypeVar

RT = TypeVar('RT')


class LRUCacheWithRemove(Generic[RT]):
    """Create a LRU cache with the option to remove keys from the cache"""

    def __init__(self, maxsize: int = 512):
        self.cache: OrderedDict[str, RT] = collections.OrderedDict()
        self.maxsize: int = maxsize

    def get(self, key: str) -> Optional[RT]:
        lowered_key = key.lower()
        if lowered_key in self.cache:
            self.cache.move_to_end(lowered_key)
            return self.cache[lowered_key]
        return None

    def set(self, key: str, value: RT) -> None:
        self.cache[key.lower()] = value
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)

    def remove(self, key: str) -> None:
        """Remove an item from the cache"""
        lowered_key = key.lower()
        if lowered_key in self.cache:
            self.cache.pop(lowered_key)

    def clear(self) -> None:
        """Delete all entries in the cache"""
        self.cache.clear()
