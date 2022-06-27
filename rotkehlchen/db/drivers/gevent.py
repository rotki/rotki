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
SQL_VM_INSTRUCTIONS_CB = 100


class DBCursor:

    def __init__(self, connection: 'DBConnection', cursor: UnderlyingCursor) -> None:  # noqa: E501
        self._cursor = cursor
        self.connection = connection

    def __iter__(self) -> 'DBCursor':
        if __debug__:
            logger.debug(f'Getting iterator for cursor {self._cursor}')
        return self

    def __next__(self) -> Any:
        """

        We type this and other function returning Any since anything else has
        too many false positives. Same as typeshed:
        https://github.com/python/typeshed/blob/a750a42c65b77963ff097b6cbb6d36cef5912eb7/stdlib/sqlite3/dbapi2.pyi#L397
        """  # noqa: E501
        if __debug__:
            logger.debug(f'Get next item for cursor {self._cursor}')
        self.connection.enter_critical_section()
        result = next(self._cursor, None)
        if result is None:
            self.connection.exit_critical_section()
            raise StopIteration()

        if __debug__:
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
        if __debug__:
            logger.debug(f'EXECUTE {statement}')
        self._cursor.execute(statement, *bindings)
        if __debug__:
            logger.debug(f'FINISH EXECUTE {statement}')
        return self

    def executemany(self, statement: str, *bindings: Sequence[Sequence]) -> 'DBCursor':
        if __debug__:
            logger.debug(f'EXECUTEMANY {statement}')
        self._cursor.executemany(statement, *bindings)
        if __debug__:
            logger.debug(f'FINISH EXECUTEMANY {statement}')
        return self

    def executescript(self, script: str) -> 'DBCursor':
        """Remember this always issues a COMMIT before
        https://docs.python.org/3/library/sqlite3.html#sqlite3.Cursor.executescript
        """
        if __debug__:
            logger.debug(f'EXECUTESCRIPT {script}')  # lgtm [py/clear-text-logging-sensitive-data]
        self._cursor.executescript(script)
        if __debug__:
            logger.debug(f'FINISH EXECUTESCRIPT {script}')  # noqa: E501 lgtm [py/clear-text-logging-sensitive-data]
        return self

    def fetchone(self) -> Any:
        if __debug__:
            logger.debug('CURSOR FETCHONE')
        result = self._cursor.fetchone()
        if __debug__:
            logger.debug('FINISH CURSOR FETCHONE')
        return result

    def fetchmany(self, size: int = None) -> List[Any]:
        if __debug__:
            logger.debug(f'CURSOR FETCHMANY with {size=}')
        if size is None:
            size = self._cursor.arraysize
        result = self._cursor.fetchmany(size)
        if __debug__:
            logger.debug('FINISH CURSOR FETCHMANY')
        return result

    def fetchall(self) -> List[Any]:
        if __debug__:
            logger.debug('CURSOR FETCHALL')
        result = self._cursor.fetchall()
        if __debug__:
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
    if __debug__:
        logger.debug('Got in the progress callback')
    gevent.sleep(0)
    if __debug__:
        logger.debug('Going out of the progress callback')
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
        if __debug__:
            logger.debug('entering critical section')
        self._in_critical_section = True
        self._conn.set_progress_handler(None, 0)

    def exit_critical_section(self) -> None:
        if __debug__:
            logger.debug('exiting critical section')
        self._in_critical_section = False
        # https://github.com/python/typeshed/issues/8105
        self._conn.set_progress_handler(progress_callback, SQL_VM_INSTRUCTIONS_CB)  # type: ignore

    def execute(self, statement: str, *bindings: Sequence) -> DBCursor:
        if __debug__:
            logger.debug(f'DB CONNECTION EXECUTE {statement}')
        underlying_cursor = self._conn.execute(statement, *bindings)
        if __debug__:
            logger.debug(f'FINISH DB CONNECTION EXECUTEMANY {statement}')
        return DBCursor(connection=self, cursor=underlying_cursor)

    def executemany(self, statement: str, *bindings: Sequence[Sequence]) -> DBCursor:
        if __debug__:
            logger.debug(f'DB CONNECTION EXECUTEMANY {statement}')
        underlying_cursor = self._conn.executemany(statement, *bindings)
        if __debug__:
            logger.debug(f'FINISH DB CONNECTION EXECUTEMANY {statement}')
        return DBCursor(connection=self, cursor=underlying_cursor)

    def executescript(self, script: str) -> DBCursor:
        """Remember this always issues a COMMIT before
        https://docs.python.org/3/library/sqlite3.html#sqlite3.Cursor.executescript
        """
        if __debug__:
            logger.debug(f'DB CONNECTION EXECUTESCRIPT {script}')
        underlying_cursor = self._conn.executescript(script)
        if __debug__:
            logger.debug(f'DB CONNECTION EXECUTESCRIPT {script}')
        return DBCursor(connection=self, cursor=underlying_cursor)

    def commit(self) -> None:
        if __debug__:
            logger.debug('START DB CONNECTION COMMIT')
        try:
            self._conn.commit()
        finally:
            self.exit_critical_section()
            if __debug__:
                logger.debug('FINISH DB CONNECTION COMMIT')

    def rollback(self) -> None:
        if __debug__:
            logger.debug('START DB CONNECTION ROLLBACK')
        try:
            self._conn.rollback()
        finally:
            self.exit_critical_section()
            if __debug__:
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

    @property
    def total_changes(self) -> int:
        """total number of database rows that have been modified, inserted,
        or deleted since the database connection was opened"""
        return self._conn.total_changes
