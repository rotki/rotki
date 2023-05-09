import collections
from collections import OrderedDict
from typing import Generic, Optional, TypeVar

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

    def add(self, key: str, value: RT) -> None:
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


class LRUSetCache(Generic[RT]):
    """
    LRU cache that works like a set.
    Internally it uses an OrderedDict to keep the order that maps to None.
    None is constant in python and it uses the minimum space possible.
    """

    def __init__(self, maxsize: int = 512):
        self.cache: OrderedDict[RT, None] = collections.OrderedDict()
        self.maxsize: int = maxsize

    def __contains__(self, key: RT) -> bool:
        return key in self.cache

    def add(self, key: RT) -> None:
        """Add an item to the cache"""
        self.cache[key] = None
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)

    def remove(self, key: RT) -> None:
        """Remove an item from the cache"""
        if key in self.cache:
            self.cache.pop(key)

    def get_values(self) -> set[RT]:
        return set(self.cache.keys())
