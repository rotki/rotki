from collections import defaultdict
from enum import Enum
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Dict, NamedTuple, Type, TypeVar

from gevent.lock import Semaphore

from rotkehlchen.errors import DeserializationError
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.typing import Timestamp


class ResultCache(NamedTuple):
    """Represents a time-cached result of some API query"""
    result: Dict
    timestamp: 'Timestamp'


# Seconds for which cached api queries will be cached
# By default 10 minutes.
# TODO: Make configurable!
CACHE_RESPONSE_FOR_SECS = 600


def _function_sig_key(name: str, arguments_matter: bool, *args: Any, **kwargs: Any) -> int:
    """Return a unique int identifying a function's call signature"""
    function_sig = name
    if arguments_matter:
        for arg in args:
            function_sig += str(arg)
        for _, value in kwargs.items():
            function_sig += str(value)

    return hash(function_sig)


class CacheableMixIn():
    """Interface for objects that can use timewise caches

    Any object that adheres to this MixIn's interface can have its functions
    use the @cache_response_timewise decorator
    """

    def __init__(self) -> None:
        super().__init__()
        self.results_cache: Dict[int, ResultCache] = {}
        # Can also be 0 which means cache is disabled.
        self.cache_ttl_secs = CACHE_RESPONSE_FOR_SECS

    def flush_cache(self, name: str, arguments_matter: bool, *args: Any, **kwargs: Any) -> None:
        cache_key = _function_sig_key(name, arguments_matter, *args, **kwargs)
        self.results_cache.pop(cache_key, None)


def cache_response_timewise(arguments_matter: bool = True) -> Callable:
    """ This is a decorator for caching results of functions of objects.
    The objects must adhere to the CachableOject interface.

    Objects adhering to this interface are:
        - all the exchanges
        - the Rotkehlchen object
        - the Blockchain object

    If the special keyword argument ignore_cache=True is given then the cache check
    is completely skipped
    """
    def _cache_response_timewise(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(wrappingobj: CacheableMixIn, *args: Any, **kwargs: Any) -> Any:
            ignore_cache = kwargs.pop('ignore_cache', False)
            cache_key = _function_sig_key(f.__name__, arguments_matter, *args, **kwargs)
            now = ts_now()
            if ignore_cache is False:
                # Check the cache
                if cache_key in wrappingobj.results_cache:
                    cache_life_secs = now - wrappingobj.results_cache[cache_key].timestamp

            cache_miss = (
                ignore_cache is True or
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


class LockableQueryMixIn():
    """Interface for objects who have queries that disallow concurrency

    Any object that adheres to this interface can have its functions
    use the @protect_with_lock decorator
    """

    def __init__(self) -> None:
        super().__init__()
        self.query_locks_map: Dict[int, Semaphore] = defaultdict(Semaphore)
        # Accessing and writing to the query_locks map also needs to be protected
        self.query_locks_map_lock = Semaphore()


def protect_with_lock(arguments_matter: bool = False) -> Callable:
    """ This is a decorator for protecting a call of an object with a lock
    The objects must adhere to the interface of having:
        - A mapping of ids to query_lock objects

    Objects adhering to this MixIn's interface(LockableQueryMixIn) are:
        - all the exchanges
        - the Blockchain object
    """
    def _cache_response_timewise(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(wrappingobj: LockableQueryMixIn, *args: Any, **kwargs: Any) -> Any:
            lock_key = _function_sig_key(f.__name__, arguments_matter, *args, **kwargs)
            with wrappingobj.query_locks_map_lock:
                lock = wrappingobj.query_locks_map[lock_key]
            with lock:
                result = f(wrappingobj, *args, **kwargs)
                return result

        return wrapper
    return _cache_response_timewise


T = TypeVar('T', bound=Enum)


class DBEnumMixIn(Enum):

    def __str__(self) -> str:
        return ' '.join(word.lower() for word in self.name.split('_'))  # pylint: disable=no-member

    def serialize_for_db(self) -> str:
        return chr(self.value + 64)

    @classmethod
    def deserialize_from_db(cls: Type[T], value: str) -> T:
        """May raise a DeserializationError if something is wrong with the DB data"""
        number = ord(value)
        if number < 65 or number > list(cls)[-1].value + 64:  # type: ignore
            raise DeserializationError(f'Failed to deserialize {cls.__name__} DB value {value}')
        return cls(number - 64)
