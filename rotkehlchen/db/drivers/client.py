"""Original code taken from here:
 https://github.com/gilesbrown/gsqlite3/blob/fef400f1c5bcbc546772c827d3992e578ea5f905/gsqlite3.py
but heavily modified"""

import random
import sqlite3
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Any, Literal, Optional, TypeAlias
from uuid import uuid4

import gevent
import zmq
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.db.checks import sanity_check_impl
from rotkehlchen.db.drivers.server import (
    DB_CONNECTION_ADDRESS,
    DBConnectionType,
    SerializedZMQReturnData,
    ZMQCallData,
    ZMQReturnData,
)
from rotkehlchen.db.minimized_schema import MINIMIZED_USER_DB_SCHEMA
from rotkehlchen.globaldb.minimized_schema import MINIMIZED_GLOBAL_DB_SCHEMA
from rotkehlchen.greenlets.utils import get_greenlet_name
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.logging import RotkehlchenLogger

UnderlyingCursor: TypeAlias = sqlite3.Cursor | sqlcipher.Cursor  # pylint: disable=no-member
UnderlyingConnection: TypeAlias = sqlite3.Connection | sqlcipher.Connection  # pylint: disable=no-member

CONTEXT_SWITCH_WAIT = 1  # seconds to wait for a status change in a DB context switch
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
            raise StopIteration

        if __debug__:
            logger.trace(f'Got next item for cursor {self._cursor}')
        return result

    def __enter__(self) -> 'DBCursor':
        return self

    def __exit__(
            self,
            exctype: type[BaseException] | None,
            value: BaseException | None,
            traceback: TracebackType | None,
    ) -> bool:
        self.close()
        return True

    def execute(self, statement: str, *bindings: Sequence) -> 'DBCursor':
        """Execute a query and return the cursor.

        Note: This should only be used for reading queries."""
        if __debug__:
            logger.trace(f'EXECUTE {statement}')
        try:
            self._cursor.execute(statement, *bindings)
        except (sqlcipher.InterfaceError, sqlite3.InterfaceError):  # pylint: disable=no-member
            # Long story. Don't judge me. https://github.com/rotki/rotki/issues/5432
            logger.debug(f'{statement} with {bindings} failed due to https://github.com/rotki/rotki/issues/5432. Retrying')  # noqa: E501
            self._cursor.execute(statement, *bindings)

        if __debug__:
            logger.trace(f'FINISH EXECUTE {statement}')
        return self

    def executemany(self, statement: str, *bindings: Sequence[Sequence]) -> 'DBCursor':
        """Execute a query with multiple bindings and return the cursor.

        Note: This should only be used for reading queries."""
        if __debug__:
            logger.trace(f'EXECUTEMANY {statement}')
        self._cursor.executemany(statement, *bindings)
        if __debug__:
            logger.trace(f'FINISH EXECUTEMANY {statement}')
        return self

    def executescript(self, script: str) -> 'DBCursor':
        """Remember this always issues a COMMIT before
        https://docs.python.org/3/library/sqlite3.html#sqlite3.Cursor.executescript

        Note: This should only be used for reading queries.
        """
        if __debug__:
            logger.trace(f'EXECUTESCRIPT {script}')
        self._cursor.executescript(script)
        if __debug__:
            logger.trace(f'FINISH EXECUTESCRIPT {script}')
        return self

    def fetchone(self) -> Any:
        if __debug__:
            logger.trace('CURSOR FETCHONE')
        result = self._cursor.fetchone()
        if __debug__:
            logger.trace('FINISH CURSOR FETCHONE')
        return result

    def fetchmany(self, size: int | None = None) -> list[Any]:
        if __debug__:
            logger.trace(f'CURSOR FETCHMANY with {size=}')
        if size is None:
            size = self._cursor.arraysize
        result = self._cursor.fetchmany(size)
        if __debug__:
            logger.trace('FINISH CURSOR FETCHMANY')
        return result

    def fetchall(self) -> list[Any]:
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


class DBWriterClient:
    def __init__(
            self,
            connection_type: 'DBConnectionType',
            db_path: str,
            zmq_connection: zmq.SyncSocket,
            open_cursor: bool = True,
    ) -> None:
        self.connection_type = connection_type
        self.db_path = db_path
        self.zmq_connection = zmq_connection
        self.rowcount: int = 0
        self.lastrowid: int = 0
        self.use_cursor = open_cursor
        if open_cursor:
            self._send('*open_cursor*')

    def _send(self, method: str, use_cursor: bool = False, *args: Any, **kwargs: Any) -> None:
        self.zmq_connection.send_pyobj(ZMQCallData(
            connection_type=self.connection_type,
            db_path=self.db_path,
            use_cursor=use_cursor,
            method=method,
            args=args,
            kwargs=kwargs,
        ))
        response: SerializedZMQReturnData | None = self.zmq_connection.recv_pyobj()
        if response is None:
            return
        result = ZMQReturnData.deserialize(response)
        if result.error is not None:
            raise result.error
        if result.result is not None:
            self.lastrowid = result.result['lastrowid']
            self.rowcount = result.result['rowcount']

    def connect(self, *args: Any, **kwargs: Any) -> None:
        gevent.wait([gevent.spawn(self._send, '__init__', *args, **kwargs)])

    def execute(self, statement: str, *bindings: Sequence[Any]) -> None:
        if __debug__:
            logger.trace(f'EXECUTE {statement}')
        try:
            self._send('execute', self.use_cursor, statement, *bindings)
        except (sqlcipher.InterfaceError, sqlite3.InterfaceError):  # pylint: disable=no-member
            # Long story. Don't judge me. https://github.com/rotki/rotki/issues/5432
            logger.debug(f'{statement} with {bindings} failed due to https://github.com/rotki/rotki/issues/5432. Retrying')  # noqa: E501
            self._send('execute', self.use_cursor, statement, *bindings)

        if __debug__:
            logger.trace(f'FINISH EXECUTE {statement}')

    def executemany(self, statement: str, *bindings: Sequence[Sequence]) -> None:
        if __debug__:
            logger.trace(f'EXECUTEMANY {statement}')
        self._send('executemany', self.use_cursor, statement, *bindings)
        if __debug__:
            logger.trace(f'FINISH EXECUTEMANY {statement}')

    def executescript(self, script: str) -> None:
        """Remember this always issues a COMMIT before
        https://docs.python.org/3/library/sqlite3.html#sqlite3.Cursor.executescript
        """
        if __debug__:
            logger.trace(f'EXECUTESCRIPT {script}')
        self._send('executescript', self.use_cursor, script)
        if __debug__:
            logger.trace(f'FINISH EXECUTESCRIPT {script}')

    def rollback(self) -> None:
        self._send('rollback')

    def commit(self) -> None:
        self._send('commit')

    def close(self) -> None:
        self._send('*close_cursor*')

    def switch_foreign_keys(
            self,
            on_or_off: Literal['ON', 'OFF'],
            restart_transaction: bool = True,
    ) -> None:
        """
        Switches foreign keys ON or OFF depending on `on_or_off`. Important! When switching
        foreign keys a commit always happens which means that if you had a transaction, it might
        need to be restarted which this function does if `restart_transaction` is True.
        """
        self.executescript(f'PRAGMA foreign_keys={on_or_off};')
        if restart_transaction is True:
            self.execute('BEGIN TRANSACTION')


# This is a global connection map to be able to get the connection from inside the
# progress handler. Having a global mapping and 3 different progress callbacks is
# a sort of ugly hack. If anybody knows of a better way to make it work let's improve it.
# With this approach we have named connections and a different progress callback per connection.
CONNECTION_MAP: dict[DBConnectionType, 'DBConnection'] = {}


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
            path: str | Path,
            connection_type: DBConnectionType,
            sql_vm_instructions_cb: int,
    ) -> None:
        CONNECTION_MAP[connection_type] = self
        self._conn: UnderlyingConnection
        self.db_path = str(path)
        self.in_callback = gevent.lock.Semaphore()
        self.transaction_lock = gevent.lock.Semaphore()
        self.connection_type = connection_type
        self.sql_vm_instructions_cb = sql_vm_instructions_cb
        # We need an ordered set. Python doesn't have such thing as a standalone object, but has
        # `dict` which preserves the order of its keys. So we use dict with None values.
        self.savepoints: dict[str, None] = {}
        # These will hold the id of the greenlet where write tx/savepoints are active
        # https://www.gevent.org/api/gevent.greenlet.html#gevent.Greenlet.minimal_ident
        self.savepoint_greenlet_id: str | None = None
        self.write_greenlet_id: str | None = None
        connect_func = sqlite3.connect if connection_type == DBConnectionType.GLOBAL else sqlcipher.connect  # noqa: E501  # pylint: disable=no-member
        connect_kwargs = {
            'database': str(path),
            'check_same_thread': False,
            'isolation_level': None,
        }
        self._conn = connect_func(**connect_kwargs)
        self._set_progress_handler()
        self.minimized_schema = None
        if connection_type == DBConnectionType.USER:
            self.minimized_schema = MINIMIZED_USER_DB_SCHEMA
        elif connection_type == DBConnectionType.GLOBAL:
            self.minimized_schema = MINIMIZED_GLOBAL_DB_SCHEMA
        self.zmq_connection = zmq.Context().socket(zmq.REQ)
        self.zmq_connection.connect(DB_CONNECTION_ADDRESS)
        DBWriterClient(
            connection_type=self.connection_type,
            db_path=self.db_path,
            zmq_connection=self.zmq_connection,
            open_cursor=False,
        ).connect(**connect_kwargs)

    def execute(self, statement: str, *bindings: Sequence) -> None:
        """Execute a query and return the cursor.

        Note: This should only be used for writing queries."""
        if __debug__:
            logger.trace(f'DB CONNECTION EXECUTE {statement}')
        self.write_conn(open_cursor=False).execute(statement, *bindings)
        if __debug__:
            logger.trace(f'FINISH DB CONNECTION EXECUTEMANY {statement}')

    def executemany(self, statement: str, *bindings: Sequence[Sequence]) -> None:
        """Execute a query with multiple bindings and return the cursor.

        Note: This should only be used for writing queries."""
        if __debug__:
            logger.trace(f'DB CONNECTION EXECUTEMANY {statement}')
        self.write_conn(open_cursor=False).executemany(statement, *bindings)
        if __debug__:
            logger.trace(f'FINISH DB CONNECTION EXECUTEMANY {statement}')

    def executescript(self, script: str) -> None:
        """Remember this always issues a COMMIT before
        https://docs.python.org/3/library/sqlite3.html#sqlite3.Cursor.executescript

        Note: This should only be used for writing queries."""
        if __debug__:
            logger.trace(f'DB CONNECTION EXECUTESCRIPT {script}')
        self.write_conn(open_cursor=False).executescript(script)
        if __debug__:
            logger.trace(f'DB CONNECTION EXECUTESCRIPT {script}')

    def commit(self) -> None:
        with self.in_callback:
            if __debug__:
                logger.trace('START DB CONNECTION COMMIT')
            try:
                self.write_conn(open_cursor=False).commit()
            finally:
                if __debug__:
                    logger.trace('FINISH DB CONNECTION COMMIT')

    def rollback(self) -> None:
        with self.in_callback:
            if __debug__:
                logger.trace('START DB CONNECTION ROLLBACK')
            try:
                self.write_conn(open_cursor=False).rollback()
            finally:
                if __debug__:
                    logger.trace('FINISH DB CONNECTION ROLLBACK')

    def cursor(self) -> DBCursor:
        return DBCursor(connection=self, cursor=self._conn.cursor())

    def write_conn(self, open_cursor: bool = True) -> DBWriterClient:
        return DBWriterClient(
            connection_type=self.connection_type,
            db_path=self.db_path,
            zmq_connection=self.zmq_connection,
            open_cursor=open_cursor,
        )

    def close(self) -> None:
        self._conn.close()
        CONNECTION_MAP.pop(self.connection_type, None)

    @contextmanager
    def read_ctx(self) -> Generator['DBCursor', None, None]:
        cursor = self.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    @contextmanager
    def write_ctx(self, commit_ts: bool = False) -> Generator['DBWriterClient', None, None]:
        """Opens a transaction to the database. This should be used kept open for
        as little time as possible.

        It's possible that a write transaction tries to be opened when savepoints are being used.
        In order for savepoints to work then, we will need to open a savepoint instead of a write
        transaction in that case. This should be used sparingly.
        """
        if len(self.savepoints) != 0:
            current_id = get_greenlet_name(gevent.getcurrent())
            if current_id != self.savepoint_greenlet_id:
                # savepoint exists but in other greenlet. Wait till it's done.
                while self.savepoint_greenlet_id is not None:
                    gevent.sleep(CONTEXT_SWITCH_WAIT)
                # and now continue with the normal write context logic
            else:  # open another savepoint instead of a write transaction
                with self.savepoint_ctx() as cursor:
                    yield cursor
                    return
        # else
        with self.critical_section(), self.transaction_lock:
            cursor = self.write_conn()
            self.write_greenlet_id = get_greenlet_name(gevent.getcurrent())
            cursor.execute('BEGIN TRANSACTION')
            try:
                yield cursor
            except Exception:
                cursor.rollback()
                raise
            else:
                if commit_ts is True:
                    cursor.execute(
                        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                        ('last_write_ts', str(ts_now())),
                    )
                    # last_write_ts in not cached to cached settings. This is a critical section
                    # and adding even one more function call can have very ugly and
                    # detrimental effects in the entire codebase as everything calls this.
                cursor.commit()
            finally:
                cursor.close()
                self.write_greenlet_id = None

    @contextmanager
    def savepoint_ctx(
            self,
            savepoint_name: str | None = None,
    ) -> Generator['DBWriterClient', None, None]:
        """
        Creates a savepoint context with the provided name. If the code inside the savepoint fails,
        rolls back this savepoint, otherwise releases it (aka forgets it -- this is not commited to the DB).
        Savepoints work like nested transactions, more information here: https://www.sqlite.org/lang_savepoint.html
        """    # noqa: E501
        cursor, savepoint_name = self._enter_savepoint(savepoint_name)
        try:
            yield cursor
        except Exception:
            self.rollback_savepoint(cursor, savepoint_name)
            raise
        finally:
            self.release_savepoint(cursor, savepoint_name)

    def _enter_savepoint(self, savepoint_name: str | None = None) -> tuple['DBWriterClient', str]:
        """
        Creates an sqlite savepoint with the given name. If None is given, a uuid is created.
        Returns cursor and savepoint's name.

        Should only be used inside a savepoint_ctx

        May raise:
        - ContextError if a savepoint with the same name already exists. Can only happen in case of
        manually specified name.
        """
        if savepoint_name is None:
            savepoint_name = str(uuid4())

        current_id = get_greenlet_name(gevent.getcurrent())
        if self._conn.in_transaction is True and self.write_greenlet_id != current_id:
            # a transaction is open in a different greenlet
            while self.write_greenlet_id is not None:
                gevent.sleep(CONTEXT_SWITCH_WAIT)  # wait until that transaction ends

        if self.savepoint_greenlet_id is not None:
            # savepoints exist but in other greenlet
            while self.savepoint_greenlet_id is not None and current_id != self.savepoint_greenlet_id:  # noqa: E501
                gevent.sleep(CONTEXT_SWITCH_WAIT)  # wait until no other savepoint exists
        if savepoint_name in self.savepoints:
            raise ContextError(
                f'Wanted to enter savepoint {savepoint_name} but a savepoint with the same name '
                f'already exists. Current savepoints: {list(self.savepoints)}',
            )
        cursor = self.write_conn(open_cursor=False)
        cursor.execute(f'SAVEPOINT "{savepoint_name}"')
        self.savepoints[savepoint_name] = None
        self.savepoint_greenlet_id = current_id
        return cursor, savepoint_name

    def _modify_savepoint(
            self,
            rollback_or_release: Literal['ROLLBACK TO', 'RELEASE'],
            cursor: 'DBWriterClient',
            savepoint_name: str | None,
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
        cursor.execute(f'{rollback_or_release} SAVEPOINT "{savepoint_name}"')

        # Release all savepoints until, and including, the one with name `savepoint_name`.
        # For rollback we don't remove the savepoints since they are not released yet.
        if rollback_or_release == 'RELEASE':
            self.savepoints = dict.fromkeys(list_savepoints[:list_savepoints.index(savepoint_name)])  # noqa: E501
            if len(self.savepoints) == 0:  # mark if we are out of all savepoints
                self.savepoint_greenlet_id = None

    def rollback_savepoint(
            self,
            cursor: 'DBWriterClient',
            savepoint_name: str | None = None,
    ) -> None:
        """
        Rollbacks to `savepoint_name` if given and to the latest savepoint otherwise.
        May raise:
        - ContextError if savepoints stack is empty or given savepoint name is not in the stack
        """
        self._modify_savepoint(
            rollback_or_release='ROLLBACK TO',
            savepoint_name=savepoint_name,
            cursor=cursor,
        )

    def release_savepoint(
            self,
            cursor: 'DBWriterClient',
            savepoint_name: str | None = None,
    ) -> None:
        """
        Releases (aka forgets) `savepoint_name` if given and the latest savepoint otherwise.
        May raise:
        - ContextError if savepoints stack is empty or given savepoint name is not in the stack
        """
        self._modify_savepoint(
            rollback_or_release='RELEASE',
            savepoint_name=savepoint_name,
            cursor=cursor,
        )

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

    @contextmanager
    def critical_section_and_transaction_lock(self) -> Generator[None, None, None]:
        with self.critical_section(), self.transaction_lock:
            yield

    @property
    def total_changes(self) -> int:
        """total number of database rows that have been modified, inserted,
        or deleted since the database connection was opened"""
        return self._conn.total_changes

    def schema_sanity_check(self) -> None:
        """Ensures that database schema is not broken.

        If you need to regenerate the schema that is being checked run:
        tools/scripts/generate_minimized_db_schema.py

        Raises DBSchemaError if anything is off.
        """
        assert (
            self.connection_type != DBConnectionType.TRANSIENT and
            self.minimized_schema is not None
        )

        with self.read_ctx() as cursor:
            sanity_check_impl(
                cursor=cursor,
                db_name=self.connection_type.name.lower(),
                minimized_schema=self.minimized_schema,
            )


if __name__ == '__main__':
    import shutil

    from rotkehlchen.args import app_args
    from rotkehlchen.config import default_data_directory
    from rotkehlchen.constants.misc import GLOBALDB_NAME, GLOBALDIR_NAME
    from rotkehlchen.logging import TRACE, add_logging_level
    add_logging_level('TRACE', TRACE)
    # Creates and run a server instance.
    _args = app_args(prog='rotki', description="rotki's db process").parse_args()
    if _args.data_dir is None:
        data_dir = default_data_directory()
    else:
        data_dir = Path(_args.data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)

    global_dir = data_dir / GLOBALDIR_NAME
    global_dir.mkdir(parents=True, exist_ok=True)
    dbname = global_dir / GLOBALDB_NAME
    if not dbname.is_file():
        # if no global db exists, copy the built-in file
        root_dir = Path(__file__).resolve().parent.parent
        builtin_data_dir = root_dir / 'data'
        shutil.copyfile(builtin_data_dir / GLOBALDB_NAME, global_dir / GLOBALDB_NAME)

    _conn = DBConnection(
        path=global_dir / GLOBALDB_NAME,
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=_args.sqlite_instructions,
    )

    with _conn.read_ctx() as _cursor, _conn.write_ctx() as write_cursor:
        write_cursor.execute('INSERT OR REPLACE INTO settings(name, value) VALUES("key", "write_ctx")')  # noqa: E501
        print(_cursor.execute('SELECT * FROM settings WHERE name = "key"').fetchall())  # noqa: T201

    with _conn.read_ctx() as _cursor, _conn.savepoint_ctx() as write_cursor:
        write_cursor.execute('INSERT OR REPLACE INTO settings(name, value) VALUES("key", "savepoint_ctx")')  # noqa: E501
        print(_cursor.execute('SELECT * FROM settings WHERE name = "key"').fetchall())  # noqa: T201
