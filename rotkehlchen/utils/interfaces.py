from collections import defaultdict
from functools import wraps
from typing import Any, Callable, Dict

from gevent.lock import Semaphore

from rotkehlchen.constants import CACHE_RESPONSE_FOR_SECS
from rotkehlchen.typing import ResultCache
from rotkehlchen.utils.misc import ts_now


def _function_sig_key(name: str, *args: Any, **kwargs: Any) -> int:
    """Return a unique int identifying a function's call signature"""
    function_sig = name
    for arg in args:
        function_sig += str(arg)
    for _, value in kwargs.items():
        function_sig += str(value)

    return hash(function_sig)


class CacheableObject():
    """Interface for objects that can use timewise caches

    Any object that adheres to this interface can have its functions
    use the @cache_response_timewise decorator
    """

    def __init__(self) -> None:
        super().__init__()
        self.results_cache: Dict[int, ResultCache] = {}
        # Can also be 0 which means cache is disabled.
        self.cache_ttl_secs = CACHE_RESPONSE_FOR_SECS


def cache_response_timewise() -> Callable:
    """ This is a decorator for caching results of functions of objects.
    The objects must adhere to the CachableOject interface.

    Objects adhering to this interface are:
        - all the exchanges
        - the Rotkehlchen object
        - the Blockchain object
    """
    def _cache_response_timewise(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(wrappingobj: CacheableObject, *args: Any, **kwargs: Any) -> Any:

            cache_key = _function_sig_key(f.__name__, *args, **kwargs)
            # Check the cache
            now = ts_now()
            if cache_key in wrappingobj.results_cache:
                cache_life_secs = now - wrappingobj.results_cache[cache_key].timestamp

            cache_miss = (
                cache_key not in wrappingobj.results_cache or
                cache_life_secs >= wrappingobj.cache_ttl_secs
            )

            if cache_miss:
                # Call the function, write the result in cache and return it
                result = f(wrappingobj, *args, **kwargs)
                wrappingobj.results_cache[cache_key] = ResultCache(result, now)
                return result

            # else hit the cache and return it
            return wrappingobj.results_cache[cache_key].result

        return wrapper
    return _cache_response_timewise


class LockableQueryObject():
    """Interface for objects who have queries that disallow concurrency

    Any object that adheres to this interface can have its functions
    use the @protect_with_lock decorator
    """

    def __init__(self) -> None:
        super().__init__()
        self.query_locks_map: Dict[int, Semaphore] = defaultdict(Semaphore)
        # Accessing and writing to the query_locks map also needs to be protected
        self.query_locks_map_lock = Semaphore()


def protect_with_lock() -> Callable:
    """ This is a decorator for protecting a call of an object with a lock
    The objects must adhere to the interface of having:
        - A mapping of ids to query_lock objects

    Objects adhering to this interface(LockableQueryObject) are:
        - all the exchanges
        - the Blockchain object
    """
    def _cache_response_timewise(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(wrappingobj: LockableQueryObject, *args: Any, **kwargs: Any) -> Any:
            lock_key = _function_sig_key(f.__name__, *args, **kwargs)
            with wrappingobj.query_locks_map_lock:
                lock = wrappingobj.query_locks_map[lock_key]
            with lock:
                result = f(wrappingobj, *args, **kwargs)
                return result

        return wrapper
    return _cache_response_timewise
