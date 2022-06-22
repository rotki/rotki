"""Original code taken from here:
 https://github.com/gilesbrown/gsqlite3/blob/fef400f1c5bcbc546772c827d3992e578ea5f905/gsqlite3.py
but heavily modified"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from types import TracebackType
from typing import Any, Generator, List, Optional, Sequence, Type, Union

import gevent
from pysqlcipher3 import dbapi2 as sqlcipher

UnderlyingCursor = Union[sqlite3.Cursor, sqlcipher.Cursor]  # pylint: disable=no-member
UnderlyingConnection = Union[sqlite3.Connection, sqlcipher.Connection]  # pylint: disable=no-member


import logging

logger = logging.getLogger(__name__)
FAST_ENOUGH = object()
TOO_SLOW = 0.001
SQL_VM_INSTRUCTIONS_CB = 100


def init_moving_average(initial: float, window_size: int = 10) -> Sequence[Optional[float]]:
    return [None] + [initial] * (window_size - 1)  # type: ignore


def update_average(value: float, values: List[Optional[float]]) -> float:
    i = values.index(None)
    values[i] = value
    average = sum(values) / len(values)  # type: ignore
    values[(i + 1) % len(values)] = None
    return average


TEMP_DEBUG = True


class DBCursor:

    def __init__(self, connection: 'DBConnection', cursor: UnderlyingCursor) -> None:  # noqa: E501
        self._cursor = cursor
        self.connection = connection

    def __iter__(self) -> 'DBCursor':
        if TEMP_DEBUG:
            logger.debug(f'Getting iterator for cursor {self._cursor}')
        # result = self._cursor.__iter__()
        result = self
        if TEMP_DEBUG:
            logger.debug(f'Got iterator for cursor {self._cursor}')
        return result

    def __next__(self) -> Any:
        """

        We type this and other function returning Any since anything else has
        too many false positives. Same as typeshed:
        https://github.com/python/typeshed/blob/a750a42c65b77963ff097b6cbb6d36cef5912eb7/stdlib/sqlite3/dbapi2.pyi#L397
        """  # noqa: E501
        if TEMP_DEBUG:
            logger.debug(f'Get next item for cursor {self._cursor}')
        self.connection.enter_critical_section()
        result = next(self._cursor, None)
        if result is None:
            self.connection.exit_critical_section()
            raise StopIteration()

        if TEMP_DEBUG:
            logger.debug(f'Got next item for cursor {self._cursor}')
        return result

    def __enter__(self) -> 'DBCursor':
        return self

    def __exit__(
            self,
            exctype: Optional[Type[BaseException]],
            value: Optional[Type[BaseException]],
            traceback: Optional[TracebackType],
    ) -> bool:
        self.close()
        return True

    def execute(self, statement: str, *bindings: Sequence) -> 'DBCursor':
        if TEMP_DEBUG:
            logger.debug(f'EXECUTE {statement}')
        self._cursor.execute(statement, *bindings)
        if TEMP_DEBUG:
            logger.debug(f'FINISH EXECUTE {statement}')
        return self

    def executemany(self, statement: str, *bindings: Sequence[Sequence]) -> 'DBCursor':
        if TEMP_DEBUG:
            logger.debug(f'EXECUTEMANY {statement}')
        self._cursor.executemany(statement, *bindings)
        if TEMP_DEBUG:
            logger.debug(f'FINISH EXECUTEMANY {statement}')
        return self

    def executescript(self, script: str) -> 'DBCursor':
        """Remember this always issues a COMMIT before
        https://docs.python.org/3/library/sqlite3.html#sqlite3.Cursor.executescript
        """
        if TEMP_DEBUG:
            logger.debug(f'EXECUTESCRIPT {script}')
        self._cursor.executescript(script)
        if TEMP_DEBUG:
            logger.debug(f'FINISH EXECUTESCRIPT {script}')
        return self

    def fetchone(self) -> Any:
        if TEMP_DEBUG:
            logger.debug('CURSOR FETCHONE')
        result = self._cursor.fetchone()
        if TEMP_DEBUG:
            logger.debug('FINISH CURSOR FETCHONE')
        return result

    def fetchmany(self, size: int = None) -> List[Any]:
        if TEMP_DEBUG:
            logger.debug(f'CURSOR FETCHMANY with {size=}')
        if size is None:
            size = self._cursor.arraysize
        result = self._cursor.fetchmany(size)
        if TEMP_DEBUG:
            logger.debug('FINISH CURSOR FETCHMANY')
        return result

    # def fetchall(self) -> Sequence[Tuple]:
    def fetchall(self) -> List[Any]:
        if TEMP_DEBUG:
            logger.debug('CURSOR FETCHALL')
        result = self._cursor.fetchall()
        if TEMP_DEBUG:
            logger.debug('FINISH CURSOR FETCHALL')
        return result

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    @property
    def lastrowid(self) -> int:
        return self._cursor.lastrowid  # type: ignore

    def close(self) -> None:
        self._cursor.close()


def progress_callback() -> int:
    # logger.debug('Got in the progress callback')
    gevent.sleep(0)
    # logger.debug('Going out of the progress callback')
    return 0


class DBConnection:

    def __init__(self, path: Union[str, Path], use_sqlcipher: bool) -> None:
        self._conn: UnderlyingConnection
        if use_sqlcipher is True:
            self._conn = sqlcipher.connect(path, check_same_thread=False)  # pylint: disable=no-member  # noqa: E501
        else:
            self._conn = sqlite3.connect(path, check_same_thread=False)

        self._in_critical_section = False
        self._conn.set_progress_handler(progress_callback, SQL_VM_INSTRUCTIONS_CB)

    def enter_critical_section(self) -> None:
        logger.debug('entering critical section')
        self._in_critical_section = True
        self._conn.set_progress_handler(None, 0)

    def exit_critical_section(self) -> None:
        logger.debug('exiting critical section')
        self._in_critical_section = False
        # https://github.com/python/typeshed/issues/8105
        self._conn.set_progress_handler(progress_callback, SQL_VM_INSTRUCTIONS_CB)  # type: ignore

    def execute(self, statement: str, *bindings: Sequence) -> DBCursor:
        if TEMP_DEBUG:
            logger.debug(f'DB CONNECTION EXECUTE {statement}')
        underlying_cursor = self._conn.execute(statement, *bindings)
        if TEMP_DEBUG:
            logger.debug(f'FINISH DB CONNECTION EXECUTEMANY {statement}')
        return DBCursor(connection=self, cursor=underlying_cursor)

    def executemany(self, statement: str, *bindings: Sequence[Sequence]) -> DBCursor:
        if TEMP_DEBUG:
            logger.debug(f'DB CONNECTION EXECUTEMANY {statement}')
        underlying_cursor = self._conn.executemany(statement, *bindings)
        if TEMP_DEBUG:
            logger.debug(f'FINISH DB CONNECTION EXECUTEMANY {statement}')
        return DBCursor(connection=self, cursor=underlying_cursor)

    def executescript(self, script: str) -> DBCursor:
        """Remember this always issues a COMMIT before
        https://docs.python.org/3/library/sqlite3.html#sqlite3.Cursor.executescript
        """
        if TEMP_DEBUG:
            logger.debug(f'DB CONNECTION EXECUTESCRIPT {script}')
        underlying_cursor = self._conn.executescript(script)
        if TEMP_DEBUG:
            logger.debug(f'DB CONNECTION EXECUTESCRIPT {script}')
        return DBCursor(connection=self, cursor=underlying_cursor)

    def commit(self) -> None:
        if TEMP_DEBUG:
            logger.debug('START DB CONNECTION COMMIT')
        try:
            self._conn.commit()
        finally:
            self.exit_critical_section()
            if TEMP_DEBUG:
                logger.debug('FINISH DB CONNECTION COMMIT')

    def rollback(self) -> None:
        if TEMP_DEBUG:
            logger.debug('START DB CONNECTION ROLLBACK')
        try:
            self._conn.rollback()
        finally:
            self.exit_critical_section()
            if TEMP_DEBUG:
                logger.debug('FINISH DB CONNECTION ROLLBACK')

    def cursor(self) -> DBCursor:
        return DBCursor(connection=self, cursor=self._conn.cursor())

    def close(self) -> None:
        self._conn.close()

    @contextmanager
    def read_ctx(self) -> Generator['DBCursor', None, None]:
        cursor = self.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    @contextmanager
    def write_ctx(self) -> Generator['DBCursor', None, None]:
        cursor = self.cursor()
        try:
            yield cursor
        except Exception:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()
        finally:
            cursor.close()

# class GeventQueryContext:
#     """
#      We share this between threads/greenlets, but
#      ultimately the worst that will happen with
#      simultaneous updates is that a query will move between
#      being considered a fast query and a slow query
#      so it isn't really worth locking (the GIL is enough here)
#     """

#     def __init__(self) -> None:
#         self.conn: Union['SqliteConnection', 'SqlcipherConnection'] = None
#         self.query_speed: Dict[str, Union[object, Sequence[Optional[float]]]] = {}
#         self.counter = 0  # counter for consecutive simple calls without a yield
#         self.threadpool_query = False
#         # self.ongoing_interaction = gevent.lock.Semaphore()
#         self.ongoing_interaction = contextlib.nullcontext()

#     def using_threadpool(self, method: Callable) -> Callable:
#         """Execute method using threadpool"""
#         @wraps(method, ['__name__', '__doc__'])
#         def apply(*args: Any, **kwargs: Any) -> bool:
#             logger.debug(f'About to acquire lock in using threadpool for {method}')
#             with self.ongoing_interaction:
#                 logger.debug(f'Acquired lock in using threadpool for {method}')
#                 result = get_hub().threadpool.apply(method, args, kwargs)
#             logger.debug(f'Released lock in using threadpool for {method}')
#             return result

#         return apply

    # def maybe_execute_using_threadpool(self, method: Callable) -> Callable:
    #     """Decide whether to use threadpool or not based on execute query time"""
    #     timefunc = time.time

    #     @wraps(method, ['__name__', '__doc__'])
    #     def apply(*args: Any, **kwargs: Any) -> Any:
    #         sql: str = args[1:2]  # type: ignore
    #         moving_average = self.query_speed.get(sql, None)
    #         logger.debug(f'About to acquire lock for execute {sql}')
    #         with self.ongoing_interaction:
    #             logger.debug(f'Acquired lock for execute {sql}')
    #             if moving_average is FAST_ENOUGH:
    #                 # if self.counter >= 50:
    #                 #     logger.debug('IN CONTEXT about to call callback')
    #                 #     self._progress_callback()

    #                 logger.debug('Direct query')
    #                 t0 = timefunc()
    #                 # this query is usually fast so run it directly
    #                 result = method(*args, **kwargs)
    #                 duration = timefunc() - t0
    #                 self.counter += 1
    #                 if duration >= TOO_SLOW:
    #                     self.query_speed[sql] = init_moving_average(duration)
    #             else:
    #                 self.counter = 0
    #                 logger.debug('Threadpool query')
    #                 self.threadpool_query = True
    #                 t0 = timefunc()
    #                 # this query is usually slow so run it in another thread
    #                 result = get_hub().threadpool.apply(method, args, kwargs)
    #                 duration = timefunc() - t0
    #                 self.counter += 1
    #                 if moving_average is not None:
    #                     avg = update_average(duration, moving_average)  # type: ignore
    #                     if avg < TOO_SLOW:
    #                         self.query_speed[sql] = FAST_ENOUGH
    #                 else:
    #                     # first time we've seen this query
    #                     if duration > TOO_SLOW:
    #                         self.query_speed[sql] = init_moving_average(duration)
    #                     else:
    #                         self.query_speed[sql] = FAST_ENOUGH

    #                 self.threadpool_query = False

    #         logger.debug(f'Released lock for execute {sql}')
    #         return result
    #     return apply

    # def cursor(self) -> Union['SqliteCursor', 'SqlcipherCursor']:
    #     return self.conn.cursor()

    # def commit(self) -> None:
    #     try:
    #         self.conn.commit()
    #     finally:
    #         self.in

#     def _progress_callback(self) -> None:
#         logger.debug('progress callback')
#         # if self.threadpool_query is False and self.conn.in_transaction is False:
#         if True:
#             self.counter = 0
#             gevent.sleep(0)
#         return 0

#     def set_yield_progress(self, conn: Union['SqliteConnection', 'SqlcipherConnection']) -> None:
#         """Sets the sqlite/sqlcipher progress handler to yield every N instructions"""
#         conn.set_progress_handler(self._progress_callback, SQL_VM_INSTRUCTIONS_CB)


# def _make_gevent_friendly(
#         context: GeventQueryContext,
#         dbdriver: ModuleType,
#         dbdriver_name: Literal['sqlite', 'sqlcipher'],
# ) -> Tuple[Callable, Type, Type]:
#     """Turn the sqlite based DBDriver into a gevent friendly version"""

#     cursor_class = type(f'{dbdriver_name.capitalize()}Cursor', (dbdriver.Cursor,), {})
    # for method in [
    #         dbdriver.Cursor.executemany,
    #         dbdriver.Cursor.executescript,
    #         dbdriver.Cursor.fetchone,
    #         dbdriver.Cursor.fetchmany,
    #         dbdriver.Cursor.fetchall,
    # ]:
    #     setattr(cursor_class, method.__name__, context.using_threadpool(method))
    # cursor_class.execute = context.maybe_execute_using_threadpool(  # type: ignore
    #     dbdriver.Cursor.execute,
    # )

    # def connection_init(self: Type, *args: Any, **kwargs: Any) -> None:
    #     """ by default [py]sqlite3 checks that object methods are run in the same
    #      thread as the one that created the Connection or Cursor. If it finds
    #      they are not then an exception is raised.
    #      <https://docs.python.org/2/library/sqlite3.html#multithreading>
    #      Luckily for us we can switch this check off.
    #     """
    #     kwargs['check_same_thread'] = False
    #     super(connection_class, self).__init__(*args, **kwargs)  # type: ignore

    # connection_class = type(
    #     f'{dbdriver_name.capitalize()}Cursor',
    #     (dbdriver.Connection,),
    #     {
    #         '__init__': connection_init,
    #         'cursor': lambda self: cursor_class(self),  # pylint:disable=unnecessary-lambda
    #     },
    # )

    # connection_class.execute = context.maybe_execute_using_threadpool(  # type: ignore
    #     dbdriver.Connection.execute,
    # )
    # for method in [
    #         dbdriver.Connection.commit,
    #         dbdriver.Connection.rollback,
    # ]:
    #     setattr(connection_class, method.__name__, context.using_threadpool(method))

    # @wraps(dbdriver.connect)
    # def new_connect(*args: Any, **kwargs: Any) -> None:
    #     kwargs['factory'] = connection_class
    #     return dbdriver.connect(*args, **kwargs)

    # return new_connect, cursor_class, connection_class


# SQLITE_CONTEXT = GeventQueryContext()
# _sqlite_connect, _, _ = _make_gevent_friendly(
#     context=SQLITE_CONTEXT,
#     dbdriver=sqlite3,
#     dbdriver_name='sqlite',
# )
# def sqlite_connect(path: str) -> GeventQueryContext:
#     conn = _sqlite_connect(path)
#     SQLITE_CONTEXT.conn = conn
#     SQLITE_CONTEXT.set_yield_progress(conn)
#     return conn

# SQLCIPHER_CONTEXT = GeventQueryContext()
# _sqlcipher_connect, _, _ = _make_gevent_friendly(
#     context=SQLCIPHER_CONTEXT,
#     dbdriver=sqlcipher,
#     dbdriver_name='sqlcipher',
# )
# def sqlcipher_connect(path: str) -> GeventQueryContext:
#     conn = _sqlcipher_connect(path)
#     SQLCIPHER_CONTEXT.conn = conn
#     SQLCIPHER_CONTEXT.set_yield_progress(conn)
#     return conn
