import collections
from collections import OrderedDict
from threading import Lock
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

KT = TypeVar('KT')  # key type
VT = TypeVar('VT')  # value type


class LRUCacheWithRemove[KT, VT]:
    """Create a LRU cache with the option to remove keys from the cache.

    Instances are shared process-wide (e.g. the Inquirer price cache and the
    AssetResolver caches are used by every task), and every operation is a
    multi-step mutation of the underlying OrderedDict, so all operations hold a
    lock. Under gevent monkeypatching the lock is cooperative and uncontended
    acquisition is cheap; after the migration to real threads it is what keeps
    concurrent get/add/remove from corrupting the LRU order or raising KeyError.
    """

    def __init__(self, maxsize: int = 512):
        self.cache: OrderedDict[KT, VT] = collections.OrderedDict()
        self.maxsize: int = maxsize
        self.lock = Lock()

    def get(self, key: KT) -> VT | None:
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            return None

    def add(self, key: KT, value: VT) -> None:
        with self.lock:
            self.cache[key] = value
            if len(self.cache) > self.maxsize:
                self.cache.popitem(last=False)

    def remove(self, key: KT) -> None:
        with self.lock:
            if key in self.cache:
                self.cache.pop(key)

    def clear(self) -> None:
        """Delete all entries in the cache"""
        with self.lock:
            self.cache.clear()

    def __iter__(self) -> Iterator[KT]:
        return self.cache.__iter__()

    def __contains__(self, key: KT) -> bool:
        return key in self.cache

    def snapshot_keys(self) -> list[KT]:
        """A point-in-time copy of the keys, safe to iterate while others mutate"""
        with self.lock:
            return list(self.cache)


class DefaultLRUCache(LRUCacheWithRemove[KT, VT]):
    """LRU cache that behaves like defaultdict when accessing objects"""

    def __init__(self, default_factory: Callable[[], VT], maxsize: int = 512):
        super().__init__(maxsize)
        self.default_factory = default_factory

    def get(self, key: KT) -> VT:
        with self.lock:  # membership check and default creation must be one atomic step,
            # otherwise two concurrent gets create two defaults and the one that loses
            # the overwrite race keeps mutating an object no longer in the cache
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]

            value = self.default_factory()
            self.cache[key] = value
            if len(self.cache) > self.maxsize:
                self.cache.popitem(last=False)
            return value


class LRUCacheLowerKey(LRUCacheWithRemove[str, VT]):
    """Create an LRU cache with string key which is always considered as lowercase"""
    def get(self, key: str) -> VT | None:
        return super().get(key.lower())

    def add(self, key: str, value: VT) -> None:
        super().add(key.lower(), value)

    def remove(self, key: str) -> None:
        super().remove(key.lower())


class LRUSetCache[VT]:
    """
    LRU cache that works like a set.
    Internally it uses an OrderedDict In order to be able to keep the order of insertion
    so that the LRU mechanism can function. None used as value since is constant in python
    and it uses the minimum space possible.

    Locked for the same reason as LRUCacheWithRemove.
    """

    def __init__(self, maxsize: int = 512):
        self.cache: OrderedDict[VT, None] = collections.OrderedDict()
        self.maxsize: int = maxsize
        self.lock = Lock()

    def __contains__(self, key: VT) -> bool:
        return key in self.cache

    def add(self, key: VT) -> None:
        """Add an item to the cache"""
        with self.lock:
            self.cache[key] = None
            if len(self.cache) > self.maxsize:
                self.cache.popitem(last=False)

    def remove(self, key: VT) -> None:
        """Remove an item from the cache"""
        with self.lock:
            if key in self.cache:
                self.cache.pop(key)
