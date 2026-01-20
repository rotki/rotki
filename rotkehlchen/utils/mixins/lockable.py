import logging
from collections import defaultdict
from collections.abc import Callable
from functools import wraps
from typing import Any

from gevent.lock import Semaphore

from rotkehlchen.logging import RotkehlchenLogsAdapter

from .common import function_sig_key

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def skip_if_running(f: Callable) -> Callable:
    """Decorator that skips execution if the function is already running.
    For class/instance methods, use LockableQueryMixIn with protect_with_lock instead.
    """
    lock = Semaphore()

    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not lock.acquire(blocking=False):
            log.debug(f'{f.__name__} already running, skipping')
            return None
        try:
            return f(*args, **kwargs)
        finally:
            lock.release()

    return wrapper


class LockableQueryMixIn:
    """Interface for objects who have queries that disallow concurrency

    Any object that adheres to this interface can have its functions
    use the @protect_with_lock decorator
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.query_locks_map: dict[int, Semaphore] = defaultdict(Semaphore)
        # Accessing and writing to the query_locks map also needs to be protected
        self.query_locks_map_lock = Semaphore()


def protect_with_lock(arguments_matter: bool = False, skip_ignore_cache: bool = False) -> Callable:
    """ This is a decorator for protecting a call of an object with a lock
    The objects must adhere to the interface of having:
        - A mapping of ids to query_lock objects

    Objects adhering to this MixIn's interface(LockableQueryMixIn) are:
        - all the exchanges
        - the Blockchain object
        - EvmNodeInquirer
    """
    def _protect_with_lock(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(wrappingobj: LockableQueryMixIn, *args: Any, **kwargs: Any) -> Any:
            lock_key = function_sig_key(
                f.__name__,        # name
                arguments_matter,  # arguments_matter
                skip_ignore_cache,  # skip_ignore_cache
                *args,
                **kwargs,
            )
            with wrappingobj.query_locks_map_lock:
                lock = wrappingobj.query_locks_map[lock_key]
            with lock:
                return f(wrappingobj, *args, **kwargs)

        return wrapper
    return _protect_with_lock
