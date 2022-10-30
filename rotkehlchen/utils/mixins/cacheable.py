from copy import deepcopy
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Dict, NamedTuple, Tuple

from rotkehlchen.utils.misc import ts_now

from .common import function_sig_key

if TYPE_CHECKING:
    from rotkehlchen.types import Timestamp


class ResultCache(NamedTuple):
    """Represents a time-cached result of some API query"""
    result: Dict
    timestamp: 'Timestamp'


# Seconds for which cached api queries will be cached
# By default 10 minutes.
# TODO: Make configurable!
CACHE_RESPONSE_FOR_SECS = 600


class CacheableMixIn:
    """Interface for objects that can use timewise caches

    Any object that adheres to this MixIn's interface can have its functions
    use the @cache_response_timewise decorator
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.results_cache: Dict[int, ResultCache] = {}
        # Can also be 0 which means cache is disabled.
        self.cache_ttl_secs = CACHE_RESPONSE_FOR_SECS

    def flush_cache(self, name: str, *args: Any, **kwargs: Any) -> None:
        cache_key = function_sig_key(
            name,
            True,  # arguments_matter
            True,  # skip_ignore_cache
            *args,
            **kwargs,
        )
        self.results_cache.pop(cache_key, None)


def _cache_response_timewise_base(
        wrappingobj: CacheableMixIn,
        f: Callable,
        arguments_matter: bool,
        forward_ignore_cache: bool,
        *args: Any,
        **kwargs: Any,
) -> Tuple[bool, int, 'Timestamp', Dict]:
    """Base code used in the 2 cache_response_timewise decorators"""
    if forward_ignore_cache:
        ignore_cache = kwargs.get('ignore_cache', False)
    else:
        ignore_cache = kwargs.pop('ignore_cache', False)
    cache_key = function_sig_key(
        f.__name__,        # name
        arguments_matter,  # arguments_matter
        True,              # skip_ignore_cache
        *args,
        **kwargs,
    )
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
    return cache_miss, cache_key, now, kwargs


def cache_response_timewise(
        arguments_matter: bool = True,
        forward_ignore_cache: bool = False,
) -> Callable:
    """ This is a decorator for caching results of functions of objects.
    The objects must adhere to the CachableOject interface.

    **Important note**: The returned dict is mutable and if mutated will mutate the
    cache itself. So handle with care. Caller should never mutate the result.
    There is a version of the decorator
    cache_response_timewise_immutable which protects against this and allows caller
    to mutate the result.

    Objects adhering to this interface are:
        - all the exchanges
        - the Rotkehlchen object
        - the Blockchain object

    If the special keyword argument ignore_cache=True is given then the cache check
    is completely skipped

    If arguments_matter is True then a different cache is kept for each different
    combination of arguments.

    if forward_ignore_cache is True then if the ignore_cache argument is given it's
    forward to the decorated function instead of being silently consumed.
    """
    def _cache_response_timewise(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(wrappingobj: CacheableMixIn, *args: Any, **kwargs: Any) -> Any:
            cache_miss, cache_key, now, kwargs = _cache_response_timewise_base(
                wrappingobj,
                f,
                arguments_matter,
                forward_ignore_cache,
                *args,
                **kwargs,
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


def cache_response_timewise_immutable(
        arguments_matter: bool = True,
        forward_ignore_cache: bool = False,
) -> Callable:
    """ Same as cache_response_timewise but resulting dict is a copy so, the cache
    itself can't be mutated.
    """
    def _cache_response_timewise(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(wrappingobj: CacheableMixIn, *args: Any, **kwargs: Any) -> Any:
            cache_miss, cache_key, now, kwargs = _cache_response_timewise_base(
                wrappingobj,
                f,
                arguments_matter,
                forward_ignore_cache,
                *args,
                **kwargs,
            )
            if cache_miss:
                # Call the function, and write the result in cache
                result = f(wrappingobj, *args, **kwargs)
                wrappingobj.results_cache[cache_key] = ResultCache(result, now)

            # in any case return a copy of the cache to avoid potential mutation
            return deepcopy(wrappingobj.results_cache[cache_key].result)

        return wrapper
    return _cache_response_timewise
