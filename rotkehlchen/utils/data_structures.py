import collections
from collections import OrderedDict
from typing import Generic, Optional, TypeVar

KT = TypeVar('KT')  # key type
VT = TypeVar('VT')  # value type


class LRUCacheWithRemove(Generic[KT, VT]):
    """Create a LRU cache with the option to remove keys from the cache"""

    def __init__(self, maxsize: int = 512):
        self.cache: OrderedDict[KT, VT] = collections.OrderedDict()
        self.maxsize: int = maxsize

    def get(self, key: KT) -> Optional[VT]:
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def add(self, key: KT, value: VT) -> None:
        self.cache[key] = value
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)

    def remove(self, key: KT) -> None:
        if key in self.cache:
            self.cache.pop(key)

    def clear(self) -> None:
        """Delete all entries in the cache"""
        self.cache.clear()


class LRUCacheLowerKey(LRUCacheWithRemove[str, VT]):
    """Create an LRU cache with string key which is always considered as lowercase"""
    def get(self, key: str) -> Optional[VT]:
        return super().get(key.lower())

    def add(self, key: str, value: VT) -> None:
        super().add(key.lower(), value)

    def remove(self, key: str) -> None:
        super().remove(key.lower())


class LRUSetCache(Generic[VT]):
    """
    LRU cache that works like a set.
    Internally it uses an OrderedDict In order to be able to keep the order of insertion
    so that the LRU mechanism can function. None used as value since is constant in python
    and it uses the minimum space possible.
    """

    def __init__(self, maxsize: int = 512):
        self.cache: OrderedDict[VT, None] = collections.OrderedDict()
        self.maxsize: int = maxsize

    def __contains__(self, key: VT) -> bool:
        return key in self.cache

    def add(self, key: VT) -> None:
        """Add an item to the cache"""
        self.cache[key] = None
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)

    def remove(self, key: VT) -> None:
        """Remove an item from the cache"""
        if key in self.cache:
            self.cache.pop(key)

    def get_values(self) -> set[VT]:
        return set(self.cache.keys())
