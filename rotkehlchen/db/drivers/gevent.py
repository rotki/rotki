"""Original code taken from here:
 https://github.com/gilesbrown/gsqlite3/blob/fef400f1c5bcbc546772c827d3992e578ea5f905/gsqlite3.py
but heavily modified"""

import sqlite3
import time
from functools import wraps
from operator import attrgetter
from types import ModuleType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

from gevent.hub import get_hub
# We want to look as much like the sqlite3 DBAPI module as possible.
# The easiest way of exposing the same module interface is to do this.
# from sqlite3 import *
from pysqlcipher3 import dbapi2 as sqlcipher


def init_moving_average(initial: float, window_size: int = 10) -> Sequence[Optional[float]]:
    return [None] + [initial] * (window_size - 1)  # type: ignore


def update_average(value: float, values: List[Optional[float]]) -> float:
    i = values.index(None)
    values[i] = value
    average = sum(values) / len(values)  # type: ignore
    values[(i + 1) % len(values)] = None
    return average


def _using_threadpool(method: Callable) -> Callable:
    @wraps(method, ['__name__', '__doc__'])
    def apply(*args: Any, **kwargs: Any) -> bool:
        return get_hub().threadpool.apply(method, args, kwargs)
    return apply


FAST_ENOUGH = object()
TOO_SLOW = 0.001


class GeventQueryContext:
    """
     OK so we share this between threads/greenlets, but
     ultimately the worst that will happen with
     simultaneous updates is that a query will move between
     being considered a fast query and a slow query
     so it isn't really worth locking (the GIL is enough here)
    """

    def __init__(self) -> None:
        self.query_speed: Dict[str, Union[object, Sequence[Optional[float]]]] = {}

    def maybe_execute_using_threadpool(self, method: Callable) -> Callable:
        timefunc = time.time

        @wraps(method, ['__name__', '__doc__'])
        def apply(*args: Any, **kwargs: Any) -> Any:
            sql: str = args[1:2]  # type: ignore
            moving_average = self.query_speed.get(sql, None)
            moving_average = FAST_ENOUGH
            if moving_average is FAST_ENOUGH:
                t0 = timefunc()
                # this query is usually fast so run it directly
                result = method(*args, **kwargs)
                duration = timefunc() - t0
                if duration >= TOO_SLOW:
                    self.query_speed[sql] = init_moving_average(duration)
            else:
                t0 = timefunc()
                # this query is usually slow so run it in another thread
                result = get_hub().threadpool.apply(method, args, kwargs)
                duration = timefunc() - t0
                if moving_average is not None:
                    avg = update_average(duration, moving_average)  # type: ignore
                    if avg < TOO_SLOW:
                        self.query_speed[sql] = FAST_ENOUGH
                else:
                    # first time we've seen this query
                    if duration > TOO_SLOW:
                        self.query_speed[sql] = init_moving_average(duration)
                    else:
                        self.query_speed[sql] = FAST_ENOUGH
            return result
        return apply


def _make_gevent_friendly(
        context: GeventQueryContext,
        dbdriver: ModuleType,
        dbdriver_name: Literal['sqlite', 'sqlcipher'],
) -> Tuple[Callable, Type, Type]:
    """Turn the sqlite based DBDriver into a gevent friendly version"""

    cursor_class = type(f'{dbdriver_name.capitalize()}Cursor', (dbdriver.Cursor,), {})
    for method in [
            dbdriver.Cursor.executemany,
            dbdriver.Cursor.executescript,
            dbdriver.Cursor.fetchone,
            dbdriver.Cursor.fetchmany,
            dbdriver.Cursor.fetchall,
    ]:
        setattr(cursor_class, method.__name__, _using_threadpool(method))
        cursor_class.execute = context.maybe_execute_using_threadpool(  # type: ignore
            dbdriver.Cursor.execute,
        )

    def connection_init(self: Type, *args: Any, **kwargs: Any) -> None:
        """ by default [py]sqlite3 checks that object methods are run in the same
         thread as the one that created the Connection or Cursor. If it finds
         they are not then an exception is raised.
         <https://docs.python.org/2/library/sqlite3.html#multithreading>
         Luckily for us we can switch this check off.
        """
        kwargs['check_same_thread'] = False
        super(connection_class, self).__init__(*args, **kwargs)  # type: ignore

    connection_class = type(
        f'{dbdriver_name.capitalize()}Cursor',
        (dbdriver.Connection,),
        {
            '__init__': connection_init,
            'cursor': lambda self: cursor_class(self),  # pylint:disable=unnecessary-lambda
        },
    )

    connection_class.execute = context.maybe_execute_using_threadpool(  # type: ignore
        attrgetter('Connection.execute')(dbdriver),
    )
    for method in [
            dbdriver.Connection.commit,
            dbdriver.Connection.rollback,
    ]:
        setattr(connection_class, method.__name__, _using_threadpool(method))

    @wraps(dbdriver.connect)
    def new_connect(*args: Any, **kwargs: Any) -> None:
        kwargs['factory'] = connection_class
        return dbdriver.connect(*args, **kwargs)

    return new_connect, cursor_class, connection_class


SQLITE_CONTEXT = GeventQueryContext()
sqlite_connect, _, _ = _make_gevent_friendly(
    context=SQLITE_CONTEXT,
    dbdriver=sqlite3,
    dbdriver_name='sqlite',
)
SQLCIPHER_CONTEXT = GeventQueryContext()
sqlcipher_connect, _, _ = _make_gevent_friendly(
    context=SQLCIPHER_CONTEXT,
    dbdriver=sqlcipher,
    dbdriver_name='sqlcipher',
)

if TYPE_CHECKING:
    # These are only used for typing, since the dynamically created class from
    # _make_gevent_friendly can not be used in typing
    class SqliteCursor(sqlite3.Cursor):
        ...

    class SqliteConnection(sqlite3.Connection):

        def cursor(self) -> SqliteCursor:  # type: ignore  # pylint: disable=no-self-use
            ...

    class SqlcipherCursor(sqlcipher.Cursor):  # pylint: disable=no-member
        ...

    class SqlcipherConnection(sqlcipher.Connection):  # pylint: disable=no-member
        ...

        def cursor(self) -> SqlcipherCursor:  # pylint: disable=no-self-use
            ...
