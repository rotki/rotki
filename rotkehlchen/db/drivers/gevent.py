"""Original code taken from here:
 https://github.com/gilesbrown/gsqlite3/blob/fef400f1c5bcbc546772c827d3992e578ea5f905/gsqlite3.py
but heavily modified"""

import random
import sqlite3
from contextlib import contextmanager
from enum import Enum, auto
from pathlib import Path
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generator,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)
from uuid import uuid4

import gevent
from pysqlcipher3 import dbapi2 as sqlcipher

if TYPE_CHECKING:
    from rotkehlchen.logging import RotkehlchenLogger

UnderlyingCursor = Union[sqlite3.Cursor, sqlcipher.Cursor]  # pylint: disable=no-member
UnderlyingConnection = Union[sqlite3.Connection, sqlcipher.Connection]  # pylint: disable=no-member


import logging

logger: 'RotkehlchenLogger' = logging.getLogger(__name__)  # type: ignore


class ContextError(Exception):
    """Intended to be raised when something is wrong with db context management"""


class DBCursor:

    def __init__(self, connection: 'DBConnection', cursor: UnderlyingCursor) -> None:
        self._cursor = cursor
        self.connection = connection

    def __iter__(self) -> 'DBCursor':
        if __debug__:
            logger.trace(f'Getting iterator for cursor {self._cursor}')
        return self

    def __next__(self) -> Any:
        """
        We type this and other function returning Any since anything else has
        too many false positives. Same as typeshed:
        https://github.com/python/typeshed/blob/a750a42c65b77963ff097b6cbb6d36cef5912eb7/stdlib/sqlite3/dbapi2.pyi#L397
        """
        if __debug__:
            logger.trace(f'Get next item for cursor {self._cursor}')
        result = next(self._cursor, None)
        if result is None:
            if __debug__:
                logger.trace(f'Stopping iteration for cursor {self._cursor}')
            raise StopIteration()

        if __debug__:
            logger.trace(f'Got next item for cursor {self._cursor}')
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
        if __debug__:
            logger.trace(f'EXECUTE {statement}')
        self._cursor.execute(statement, *bindings)
        if __debug__:
            logger.trace(f'FINISH EXECUTE {statement}')
        return self

    def executemany(self, statement: str, *bindings: Sequence[Sequence]) -> 'DBCursor':
        if __debug__:
            logger.trace(f'EXECUTEMANY {statement}')
        self._cursor.executemany(statement, *bindings)
        if __debug__:
            logger.trace(f'FINISH EXECUTEMANY {statement}')
        return self

    def executescript(self, script: str) -> 'DBCursor':
        """Remember this always issues a COMMIT before
        https://docs.python.org/3/library/sqlite3.html#sqlite3.Cursor.executescript
        """
        if __debug__:
            logger.trace(f'EXECUTESCRIPT {script}')  # lgtm [py/clear-text-logging-sensitive-data]
        self._cursor.executescript(script)
        if __debug__:
            logger.trace(f'FINISH EXECUTESCRIPT {script}')  # noqa: E501 lgtm [py/clear-text-logging-sensitive-data]
        return self

    def fetchone(self) -> Any:
        if __debug__:
            logger.trace('CURSOR FETCHONE')
        result = self._cursor.fetchone()
        if __debug__:
            logger.trace('FINISH CURSOR FETCHONE')
        return result

    def fetchmany(self, size: int = None) -> List[Any]:
        if __debug__:
            logger.trace(f'CURSOR FETCHMANY with {size=}')
        if size is None:
            size = self._cursor.arraysize
        result = self._cursor.fetchmany(size)
        if __debug__:
            logger.trace('FINISH CURSOR FETCHMANY')
        return result

    def fetchall(self) -> List[Any]:
        if __debug__:
            logger.trace('CURSOR FETCHALL')
        result = self._cursor.fetchall()
        if __debug__:
            logger.trace('FINISH CURSOR FETCHALL')
        return result

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    @property
    def lastrowid(self) -> int:
        return self._cursor.lastrowid  # type: ignore

    def close(self) -> None:
        self._cursor.close()


class DBConnectionType(Enum):
    USER = auto()
    TRANSIENT = auto()
    GLOBAL = auto()


# This is a global connection map to be able to get the connection from inside the
# progress handler. Having a global mapping and 3 different progress callbacks is
# a sort of ugly hack. If anybody knows of a better way to make it work let's improve it.
# With this approach we have named connections and a different progress callback per connection.
CONNECTION_MAP: Dict[DBConnectionType, 'DBConnection'] = {}


def _progress_callback(connection: Optional['DBConnection']) -> int:
    """Needs to be a static function. Cannot be a connection class method
    or sqlite breaks in funny ways. Raises random Operational errors.
    """
    if __debug__:
        identifier = random.random()
        conn_type = connection.connection_type if connection else 'no connection'
        logger.trace(f'START progress callback for {conn_type} with id {identifier}')

    if connection is None:
        return 0

    if connection.in_callback.ready() is False:
        # This solves the bug described in test_callback_segfault_complex. This works
        # since we are single threaded and if we get here and it's locked we know that
        # we should not wait since this is an edge case that can hit us if the connection gets
        # modified before we exit the callback. So we immediately exit the callback
        # without any sleep that would lead to context switching
        return 0

    # without this rotkehlchen/tests/db/test_async.py::test_async_segfault fails
    with connection.in_callback:
        if __debug__:
            logger.trace(f'Got in locked section of the progress callback for {connection.connection_type} with id {identifier}')  # noqa: E501
        gevent.sleep(0)
        if __debug__:
            logger.trace(f'Going out of the progress callback for {connection.connection_type} with id {identifier}')  # noqa: E501
        return 0


def user_callback() -> int:
    connection = CONNECTION_MAP.get(DBConnectionType.USER)
    return _progress_callback(connection)


def transient_callback() -> int:
    connection = CONNECTION_MAP.get(DBConnectionType.TRANSIENT)
    return _progress_callback(connection)


def global_callback() -> int:
    connection = CONNECTION_MAP.get(DBConnectionType.GLOBAL)
    return _progress_callback(connection)


CALLBACK_MAP = {
    DBConnectionType.USER: user_callback,
    DBConnectionType.TRANSIENT: transient_callback,
    DBConnectionType.GLOBAL: global_callback,
}


class DBConnection:

    def _set_progress_handler(self) -> None:
        callback = CALLBACK_MAP.get(self.connection_type)
        self._conn.set_progress_handler(callback, self.sql_vm_instructions_cb)

    def __init__(
            self,
            path: Union[str, Path],
            connection_type: DBConnectionType,
            sql_vm_instructions_cb: int,
    ) -> None:
        CONNECTION_MAP[connection_type] = self
        self._conn: UnderlyingConnection
        self.in_callback = gevent.lock.Semaphore()
        self.connection_type = connection_type
        self.sql_vm_instructions_cb = sql_vm_instructions_cb
        # We need an ordered set. Python doesn't have such thing as a standalone object, but has
        # `dict` which preserves the order of its keys. So we use dict with None values.
        self.savepoints: Dict[str, None] = {}
        if connection_type == DBConnectionType.GLOBAL:
            self._conn = sqlite3.connect(path, check_same_thread=False)
        else:
            self._conn = sqlcipher.connect(path, check_same_thread=False)  # pylint: disable=no-member  # noqa: E501
        self._set_progress_handler()

    def execute(self, statement: str, *bindings: Sequence) -> DBCursor:
        if __debug__:
            logger.trace(f'DB CONNECTION EXECUTE {statement}')
        underlying_cursor = self._conn.execute(statement, *bindings)
        if __debug__:
            logger.trace(f'FINISH DB CONNECTION EXECUTEMANY {statement}')
        return DBCursor(connection=self, cursor=underlying_cursor)

    def executemany(self, statement: str, *bindings: Sequence[Sequence]) -> DBCursor:
        if __debug__:
            logger.trace(f'DB CONNECTION EXECUTEMANY {statement}')
        underlying_cursor = self._conn.executemany(statement, *bindings)
        if __debug__:
            logger.trace(f'FINISH DB CONNECTION EXECUTEMANY {statement}')
        return DBCursor(connection=self, cursor=underlying_cursor)

    def executescript(self, script: str) -> DBCursor:
        """Remember this always issues a COMMIT before
        https://docs.python.org/3/library/sqlite3.html#sqlite3.Cursor.executescript
        """
        if __debug__:
            logger.trace(f'DB CONNECTION EXECUTESCRIPT {script}')
        underlying_cursor = self._conn.executescript(script)
        if __debug__:
            logger.trace(f'DB CONNECTION EXECUTESCRIPT {script}')
        return DBCursor(connection=self, cursor=underlying_cursor)

    def commit(self) -> None:
        with self.in_callback:
            if __debug__:
                logger.trace('START DB CONNECTION COMMIT')
            try:
                self._conn.commit()
            finally:
                if __debug__:
                    logger.trace('FINISH DB CONNECTION COMMIT')

    def rollback(self) -> None:
        with self.in_callback:
            if __debug__:
                logger.trace('START DB CONNECTION ROLLBACK')
            try:
                self._conn.rollback()
            finally:
                if __debug__:
                    logger.trace('FINISH DB CONNECTION ROLLBACK')

    def cursor(self) -> DBCursor:
        return DBCursor(connection=self, cursor=self._conn.cursor())

    def close(self) -> None:
        self._conn.close()
        CONNECTION_MAP.pop(self.connection_type, None)

    @contextmanager
    def read_ctx(self) -> Generator['DBCursor', None, None]:
        cursor = self.cursor()
        try:
            yield cursor
        finally:
            cursor.close()  # lgtm [py/should-use-with]

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
            cursor.close()  # lgtm [py/should-use-with]

    @contextmanager
    def savepoint_ctx(
            self,
            savepoint_name: Optional[str] = None,
    ) -> Generator['DBCursor', None, None]:
        """
        Creates a savepoint context with the provided name. If the code inside the savepoint fails,
        rolls back this savepoint, otherwise releases it (aka forgets it -- this is not commited to the DB).
        Savepoints work like nested transactions, more information here: https://www.sqlite.org/lang_savepoint.html
        """    # noqa: E501
        cursor, savepoint_name = self.enter_savepoint(savepoint_name)
        try:
            yield cursor
        except Exception:
            self.rollback_savepoint(savepoint_name)
            raise
        else:
            self.release_savepoint(savepoint_name)
        finally:
            cursor.close()  # lgtm [py/should-use-with]

    def enter_savepoint(self, savepoint_name: Optional[str] = None) -> Tuple['DBCursor', str]:
        """
        Creates an sqlite savepoint with the given name. If None is given, a uuid is created.
        Returns cursor and savepoint's name.
        May raise:
        - ContextError if a savepoint with the same name already exists. Can only happen in case of
        manually specified name.
        """
        if savepoint_name is None:
            savepoint_name = str(uuid4())
        if savepoint_name in self.savepoints:
            raise ContextError(
                f'Wanted to enter savepoint {savepoint_name} but a savepoint with the same name '
                f'already exists. Current savepoints: {list(self.savepoints)}',
            )
        cursor = self.cursor()
        cursor.execute(f'SAVEPOINT "{savepoint_name}"')
        self.savepoints[savepoint_name] = None
        return cursor, savepoint_name

    def _modify_savepoint(
            self,
            rollback_or_release: Literal['ROLLBACK TO', 'RELEASE'],
            savepoint_name: Optional[str],
    ) -> None:
        if len(self.savepoints) == 0:
            raise ContextError(
                f'Incorrect use of savepoints! Wanted to {rollback_or_release.lower()} savepoint '
                f'{savepoint_name}, but the stack is empty.',
            )
        list_savepoints = list(self.savepoints)
        if savepoint_name is None:
            savepoint_name = list_savepoints[-1]
        elif savepoint_name not in self.savepoints:
            raise ContextError(
                f'Incorrect use of savepoints! Wanted to {rollback_or_release.lower()} savepoint '
                f'{savepoint_name}, but it is not present in the stack: {list_savepoints}',
            )
        self.execute(f'{rollback_or_release} SAVEPOINT "{savepoint_name}"')

        # Rollback all savepoints until, and including, the one with name `savepoint_name`
        self.savepoints = dict.fromkeys(list_savepoints[:list_savepoints.index(savepoint_name)])

    def rollback_savepoint(self, savepoint_name: Optional[str] = None) -> None:
        """
        Rollbacks to `savepoint_name` if given and to the latest savepoint otherwise.
        May raise:
        - ContextError if savepoints stack is empty or given savepoint name is not in the stack
        """
        self._modify_savepoint(rollback_or_release='ROLLBACK TO', savepoint_name=savepoint_name)

    def release_savepoint(self, savepoint_name: Optional[str] = None) -> None:
        """
        Releases (aka forgets) `savepoint_name` if given and the latest savepoint otherwise.
        May raise:
        - ContextError if savepoints stack is empty or given savepoint name is not in the stack
        """
        self._modify_savepoint(rollback_or_release='RELEASE', savepoint_name=savepoint_name)

    @contextmanager
    def critical_section(self) -> Generator[None, None, None]:
        with self.in_callback:
            if __debug__:
                logger.trace(f'entering critical section for {self.connection_type}')
            self._conn.set_progress_handler(None, 0)
        yield

        with self.in_callback:
            if __debug__:
                logger.trace(f'exiting critical section for {self.connection_type}')
            self._set_progress_handler()

    @property
    def total_changes(self) -> int:
        """total number of database rows that have been modified, inserted,
        or deleted since the database connection was opened"""
        return self._conn.total_changes
