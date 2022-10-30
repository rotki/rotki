from collections import defaultdict
from functools import wraps
from typing import Any, Callable, Dict

from gevent.lock import Semaphore

from .common import function_sig_key


class LockableQueryMixIn():
    """Interface for objects who have queries that disallow concurrency

    Any object that adheres to this interface can have its functions
    use the @protect_with_lock decorator
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
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
    def _protect_with_lock(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(wrappingobj: LockableQueryMixIn, *args: Any, **kwargs: Any) -> Any:
            lock_key = function_sig_key(
                f.__name__,        # name
                arguments_matter,  # arguments_matter
                False,             # skip_ignore_cache
                *args,
                **kwargs,
            )
            with wrappingobj.query_locks_map_lock:
                lock = wrappingobj.query_locks_map[lock_key]
            with lock:
                result = f(wrappingobj, *args, **kwargs)
                return result

        return wrapper
    return _protect_with_lock
