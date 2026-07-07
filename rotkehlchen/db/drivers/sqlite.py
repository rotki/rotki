"""Original code taken from here:
 https://github.com/gilesbrown/gsqlite3/blob/fef400f1c5bcbc546772c827d3992e578ea5f905/gsqlite3.py
but heavily modified

A thread-safe driver over one sqlite/sqlcipher connection shared by concurrent
tasks (the gevent yield machinery it grew out of was removed by the migration
of docs/designs/gevent_to_asyncio.md). The sqlite progress handler serves as
the cancellation checkpoint that aborts running statements of cancelled tasks.

On top of the single write connection a DBConnection can maintain a pool of
read-only connections (enable_read_pool()). With the database in WAL mode the
pooled readers run concurrently with writes and are isolated from them: a
commit/rollback on the write connection no longer resets in-flight read
statements, and readers never observe uncommitted data. read_ctx() borrows a
pooled reader transparently, falling back to the write connection when the
calling thread currently holds the write transaction or savepoint stack (so a
task keeps seeing its own uncommitted writes).
"""

import logging
import queue
import random
import threading
import time
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from enum import Enum, auto
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Any, Literal, Optional, Self, TypeAlias
from uuid import uuid4

import rsqlite
from polyleven import levenshtein
from sqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.concurrency import TaskCancelledError, checkpoint, current_token
from rotkehlchen.db.checks import sanity_check_impl
from rotkehlchen.db.minimized_schema import MINIMIZED_USER_DB_INDEXES, MINIMIZED_USER_DB_SCHEMA
from rotkehlchen.globaldb.minimized_schema import (
    MINIMIZED_GLOBAL_DB_INDEXES,
    MINIMIZED_GLOBAL_DB_SCHEMA,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.logging import RotkehlchenLogger

UnderlyingCursor: TypeAlias = rsqlite.Cursor | sqlcipher.Cursor  # pylint: disable=no-member
UnderlyingConnection: TypeAlias = rsqlite.Connection | sqlcipher.Connection  # pylint: disable=no-member

CONTEXT_SWITCH_WAIT = 0.025  # seconds between cancellation checks while waiting for the transaction slot  # noqa: E501

logger: 'RotkehlchenLogger' = logging.getLogger(__name__)  # type: ignore


class ContextError(Exception):
    """Intended to be raised when something is wrong with db context management"""


def _maybe_raise_cancelled(error: Exception) -> None:
    """Translate a statement abort triggered by the cancellation checkpoint in the
    progress callback into TaskCancelledError. No-op for any other error, so callers
    must re-raise afterwards."""
    if (
            str(error) == 'interrupted' and
            (token := current_token()) is not None and
            token.cancelled
    ):
        raise TaskCancelledError(token.reason) from error


class DBCursor:

    def __init__(self, connection: 'DBConnection', cursor: UnderlyingCursor) -> None:
        self._cursor = cursor
        self.connection = connection

    def __iter__(self) -> 'DBCursor':
        if __debug__:
            logger.trace(f'Getting iterator for cursor {id(self)}')
        return self

    def __next__(self) -> Any:
        """
        We type this and other function returning Any since anything else has
        too many false positives. Same as typeshed:
        https://github.com/python/typeshed/blob/a750a42c65b77963ff097b6cbb6d36cef5912eb7/stdlib/sqlite3/dbapi2.pyi#L397
        """
        if __debug__:
            logger.trace(f'Get next item for cursor {id(self)}')
        try:
            with self.connection.statement_lock:
                result = next(self._cursor, None)
        except (sqlcipher.OperationalError, rsqlite.OperationalError) as e:  # pylint: disable=no-member
            _maybe_raise_cancelled(e)
            raise
        if result is None:
            if __debug__:
                logger.trace(f'Stopping iteration for cursor {id(self)}')
            raise StopIteration

        if __debug__:
            logger.trace(f'Got next item for cursor {id(self)}')
        return result

    def __enter__(self) -> Self:
        return self

    def __exit__(
            self,
            exctype: type[BaseException] | None,
            value: BaseException | None,
            traceback: TracebackType | None,
    ) -> Literal[False]:
        """Closes the cursor when exiting the context.
        Returns False to indicate that exceptions should not be suppressed.
        See https://docs.python.org/3/library/stdtypes.html#contextmanager.__exit__
        """
        self.close()
        return False

    def execute(self, statement: str, *bindings: Sequence) -> 'DBCursor':
        if __debug__:
            logger.trace(f'EXECUTE {statement} with bindings {bindings} for cursor {id(self)}')
        try:
            with self.connection.statement_lock:
                try:
                    self._cursor.execute(statement, *bindings)
                except (sqlcipher.InterfaceError, rsqlite.InterfaceError) as e:  # pylint: disable=no-member
                    # Long story. Don't judge me. https://github.com/rotki/rotki/issues/5432
                    logger.debug('%s with %s failed due to %s. Probably https://github.com/rotki/rotki/issues/5432. Retrying', statement, bindings, e)  # noqa: E501
                    self._cursor.execute(statement, *bindings)
        except (sqlcipher.OperationalError, rsqlite.OperationalError) as e:  # pylint: disable=no-member
            _maybe_raise_cancelled(e)
            raise

        if __debug__:
            logger.trace(f'FINISH EXECUTE {statement} with bindings {bindings} for cursor {id(self)}')  # noqa: E501
        return self

    def executemany(
            self,
            statement: str,
            *bindings: Sequence[Sequence] | Generator[Sequence, None, None],
    ) -> 'DBCursor':
        if __debug__:
            logger.trace(f'EXECUTEMANY {statement} with bindings {bindings} for cursor {id(self)}')
        try:
            with self.connection.statement_lock:
                self._cursor.executemany(statement, *bindings)
        except (sqlcipher.OperationalError, rsqlite.OperationalError) as e:  # pylint: disable=no-member
            _maybe_raise_cancelled(e)
            raise
        if __debug__:
            logger.trace(f'FINISH EXECUTEMANY {statement} with bindings {bindings} for cursor {id(self)}')  # noqa: E501
        return self

    def executescript(self, script: str) -> 'DBCursor':
        """Remember this always issues a COMMIT before
        https://docs.python.org/3/library/sqlite3.html#sqlite3.Cursor.executescript
        """
        if __debug__:
            logger.trace(f'EXECUTESCRIPT {script} for cursor {id(self)}')
        try:
            with self.connection.statement_lock:
                self._cursor.executescript(script)
        except (sqlcipher.OperationalError, rsqlite.OperationalError) as e:  # pylint: disable=no-member
            _maybe_raise_cancelled(e)
            raise
        if __debug__:
            logger.trace(f'FINISH EXECUTESCRIPT {script} for cursor {id(self)}')
        return self

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

    def fetchone(self) -> Any:
        if __debug__:
            logger.trace(f'CURSOR FETCHONE  for cursor {id(self)}')
        try:
            with self.connection.statement_lock:
                result = self._cursor.fetchone()
        except (sqlcipher.OperationalError, rsqlite.OperationalError) as e:  # pylint: disable=no-member
            _maybe_raise_cancelled(e)
            raise
        if __debug__:
            logger.trace(f'FINISH CURSOR FETCHONE for cursor {id(self)}')
        return result

    def fetchmany(self, size: int | None = None) -> list[Any]:
        if __debug__:
            logger.trace(f'CURSOR FETCHMANY with {size=} for cursor {id(self)}')
        if size is None:
            size = self._cursor.arraysize
        try:
            with self.connection.statement_lock:
                result = self._cursor.fetchmany(size)
        except (sqlcipher.OperationalError, rsqlite.OperationalError) as e:  # pylint: disable=no-member
            _maybe_raise_cancelled(e)
            raise
        if __debug__:
            logger.trace(f'FINISH CURSOR FETCHMANY for cursor {id(self)}')
        return result

    def fetchall(self) -> list[Any]:
        if __debug__:
            logger.trace(f'CURSOR FETCHALL for cursor {id(self)}')
        try:
            with self.connection.statement_lock:
                result = self._cursor.fetchall()
        except (sqlcipher.OperationalError, rsqlite.OperationalError) as e:  # pylint: disable=no-member
            _maybe_raise_cancelled(e)
            raise
        if __debug__:
            logger.trace(f'FINISH CURSOR FETCHALL for cursor {id(self)}')
        return result

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    @property
    def lastrowid(self) -> int:
        return self._cursor.lastrowid

    def close(self) -> None:
        with self.connection.statement_lock:
            self._cursor.close()


class DBConnectionType(Enum):
    USER = auto()
    TRANSIENT = auto()
    GLOBAL = auto()
    # the read-only packaged global DB shipped with rotki. A distinct type so that
    # its connection gets its own CONNECTION_MAP slot and progress callback -- were
    # it registered as GLOBAL it would replace the main global DB connection in the
    # map, making that one's progress callback consult the wrong connection's locks
    # (and e.g. interrupt a commit the in_callback guard should have protected)
    PACKAGED_GLOBAL = auto()


# This is a global connection map to be able to get the connection from inside the
# progress handler. Having a global mapping and 3 different progress callbacks is
# a sort of ugly hack. If anybody knows of a better way to make it work let's improve it.
# With this approach we have named connections and a different progress callback per connection.
CONNECTION_MAP: dict[DBConnectionType, 'DBConnection'] = {}


def _progress_callback(connection: Optional['DBConnection']) -> int:
    """Needs to be a static function. Cannot be a connection class method
    or sqlite breaks in funny ways. Raises random Operational errors.
    """
    if connection is None:
        return 0

    if connection.in_callback.locked() or connection.in_critical_section.locked():
        # if we get here and the connection is locked or in critical section its state
        # must not be modified nor its running statement aborted from within the
        # callback (e.g. a commit is in progress). So we immediately exit the callback
        # without any sleep that would lead to context switching
        return 0

    if (token := current_token()) is not None and token.cancelled:
        # cancellation checkpoint: abort the running statement of a cancelled task.
        # sqlite raises OperationalError('interrupted') which the cursor translates
        # to TaskCancelledError. Never hit during commits/critical sections due to
        # the guard above, so driver-internal bookkeeping cannot be aborted.
        return 1

    return 0  # not cancelled: the callback is only a cancellation checkpoint


def user_callback() -> int:
    connection = CONNECTION_MAP.get(DBConnectionType.USER)
    return _progress_callback(connection)


def transient_callback() -> int:
    connection = CONNECTION_MAP.get(DBConnectionType.TRANSIENT)
    return _progress_callback(connection)


def global_callback() -> int:
    connection = CONNECTION_MAP.get(DBConnectionType.GLOBAL)
    return _progress_callback(connection)


def packaged_global_callback() -> int:
    connection = CONNECTION_MAP.get(DBConnectionType.PACKAGED_GLOBAL)
    return _progress_callback(connection)


CALLBACK_MAP = {
    DBConnectionType.USER: user_callback,
    DBConnectionType.TRANSIENT: transient_callback,
    DBConnectionType.GLOBAL: global_callback,
    DBConnectionType.PACKAGED_GLOBAL: packaged_global_callback,
}


def reader_callback() -> int:
    """Cancellation checkpoint for pooled read-only connections. Readers never
    commit or modify driver bookkeeping state, so aborting a read statement is
    always safe and none of the in_callback/in_critical_section guards of the
    write connection's callback are needed here."""
    if (token := current_token()) is not None and token.cancelled:
        return 1
    return 0


class DBConnection:

    def _set_progress_handler(self) -> None:
        callback = reader_callback if self._read_only else CALLBACK_MAP.get(self.connection_type)
        self._conn.set_progress_handler(callback, self.sql_vm_instructions_cb)

    def __init__(
            self,
            path: str | Path,
            connection_type: DBConnectionType,
            sql_vm_instructions_cb: int,
            read_only: bool = False,
    ) -> None:
        """A read_only connection is a pool reader: it is opened with mode=ro so
        sqlite rejects any write attempt, it is never registered in CONNECTION_MAP
        (registering would evict the write connection of the same type) and its
        progress callback only serves as a cancellation checkpoint."""
        self._conn: UnderlyingConnection
        self._path = path
        self._read_only = read_only
        # Pool of read-only connections lazily created by enable_read_pool(). While
        # None, read_ctx() serves cursors of this (the write) connection. The lock
        # guards the pool reference swap at close() against concurrent returns.
        self._read_pool: queue.SimpleQueue[DBConnection] | None = None
        self._read_pool_lock = threading.Lock()
        # The reader this thread has currently borrowed, so that nested read_ctx
        # calls reuse it instead of borrowing a second one. Without this, N threads
        # nesting read contexts could each hold one reader while waiting for
        # another, deadlocking once the pool is exhausted.
        self._borrowed_reader = threading.local()
        # Lock and not Semaphore since the progress callback inspects held
        # state through locked()
        self.in_callback = threading.Lock()
        self.transaction_lock = threading.Lock()
        self.in_critical_section = threading.Lock()
        # Only one thread may be inside sqlite C code for this connection at a
        # time. pysqlite takes sqlite's connection mutex while holding the GIL
        # on several paths (sqlite3_reset & co), while a concurrent statement
        # step holds that mutex with the GIL released and its progress callback
        # waiting for the GIL -- without this lock two threads deadlock on the
        # GIL/db-mutex pair. sqlite serializes per-step on one connection
        # anyway, so no real concurrency is given up. RLock so that Python
        # functions registered on the connection (e.g. levenshtein) could
        # nest DB access on the same thread without deadlocking.
        self.statement_lock = threading.RLock()
        self.connection_type = connection_type
        self.sql_vm_instructions_cb = sql_vm_instructions_cb
        # We need an ordered set. Python doesn't have such thing as a standalone object, but has
        # `dict` which preserves the order of its keys. So we use dict with None values.
        self.savepoints: dict[str, None] = {}
        # These hold threading.get_ident() of the task where write tx/savepoints are active
        self.savepoint_task_ident: int | None = None
        self.write_task_ident: int | None = None
        # whether the current savepoint stack claimed transaction_lock itself
        # (False when the savepoints nest inside this task's own write transaction)
        self._savepoint_holds_transaction_lock = False
        if connection_type in (DBConnectionType.GLOBAL, DBConnectionType.PACKAGED_GLOBAL):
            if read_only:
                # as_uri() gives a percent-encoded file:// URI that sqlite accepts
                # on all platforms (a plain f'file:{path}' breaks on windows paths)
                self._conn = rsqlite.connect(
                    database=Path(path).absolute().as_uri() + '?mode=ro',
                    uri=True,
                    check_same_thread=False,
                    isolation_level=None,
                )
            else:
                self._conn = rsqlite.connect(
                    database=path,
                    check_same_thread=False,
                    isolation_level=None,
                )
        else:
            assert read_only is False, 'read-only pool readers are not implemented for sqlcipher connections yet'  # noqa: E501
            self._conn = sqlcipher.connect(  # pylint: disable=no-member
                database=str(path),
                check_same_thread=False,
                isolation_level=None,
            )
        if not read_only:
            # Register in the map only now that the connection is fully initialized: the
            # per-type callbacks read it from other threads (e.g. an abandoned task still
            # stepping a statement on the previous connection of this type), and must
            # never observe an object whose locks/underlying connection don't exist yet
            CONNECTION_MAP[connection_type] = self
        self._set_progress_handler()
        if connection_type in (DBConnectionType.GLOBAL, DBConnectionType.PACKAGED_GLOBAL):
            # Register a fuzzy-match helper so asset search/ranking can ORDER BY Levenshtein
            # distance directly in SQL instead of pulling every matching row into memory.
            with self.statement_lock:
                self._conn.create_function('levenshtein', 2, levenshtein, deterministic=True)
        self.minimized_schema = None
        self.minimized_indexes = None
        if connection_type == DBConnectionType.USER:
            self.minimized_schema = MINIMIZED_USER_DB_SCHEMA
            self.minimized_indexes = MINIMIZED_USER_DB_INDEXES
        elif connection_type == DBConnectionType.GLOBAL:
            self.minimized_schema = MINIMIZED_GLOBAL_DB_SCHEMA
            self.minimized_indexes = MINIMIZED_GLOBAL_DB_INDEXES

    def commit(self) -> None:
        with self.in_callback:
            if __debug__:
                logger.trace('START DB CONNECTION COMMIT')
            try:
                with self.statement_lock:
                    self._conn.commit()
            finally:
                if __debug__:
                    logger.trace('FINISH DB CONNECTION COMMIT')

    def rollback(self) -> None:
        with self.in_callback:
            if __debug__:
                logger.trace('START DB CONNECTION ROLLBACK')
            try:
                with self.statement_lock:
                    self._conn.rollback()
            finally:
                if __debug__:
                    logger.trace('FINISH DB CONNECTION ROLLBACK')

    def cursor(self) -> DBCursor:
        with self.statement_lock:
            return DBCursor(connection=self, cursor=self._conn.cursor())

    def close(self) -> None:
        with self._read_pool_lock:
            read_pool, self._read_pool = self._read_pool, None
        if read_pool is not None:
            # Close the readers currently in the pool. A reader borrowed at this
            # moment is closed by _return_reader when its read_ctx exits, since
            # the pool it would be returned to is gone.
            while True:
                try:
                    read_pool.get_nowait().close()
                except queue.Empty:
                    break
        with self.statement_lock:
            self._conn.close()
        if not self._read_only:  # a reader was never registered in the map
            CONNECTION_MAP.pop(self.connection_type, None)

    def enable_read_pool(self, size: int = 4) -> None:
        """Create the pool of read-only connections that read_ctx() borrows from.

        Must only be called after the database is in WAL mode: with the default
        journal mode a writer's transaction blocks readers on other connections
        (and vice versa), while under WAL they proceed concurrently and each read
        statement sees a consistent committed snapshot.

        No-op for in-memory databases (used by tests): they cannot use WAL and
        there is no file for a second connection to open, so read_ctx() keeps
        serving cursors of this connection there.
        """
        assert self._read_only is False, 'cannot enable a read pool on a pool reader'
        if str(self._path) == ':memory:':
            return
        read_pool: queue.SimpleQueue[DBConnection] = queue.SimpleQueue()
        for _ in range(size):
            read_pool.put(DBConnection(
                path=self._path,
                connection_type=self.connection_type,
                sql_vm_instructions_cb=self.sql_vm_instructions_cb,
                read_only=True,
            ))
        with self._read_pool_lock:
            assert self._read_pool is None, 'read pool is already enabled'
            self._read_pool = read_pool

    def _borrow_reader(self, read_pool: 'queue.SimpleQueue[DBConnection]') -> 'DBConnection':
        """Blocking borrow of a pooled reader that stays responsive to task
        cancellation, mirroring _acquire_transaction_lock.

        May raise TaskCancelledError.
        """
        while True:
            try:
                return read_pool.get(timeout=CONTEXT_SWITCH_WAIT)
            except queue.Empty:
                checkpoint()  # cancelled tasks should not keep waiting for a reader

    def _return_reader(self, reader: 'DBConnection') -> None:
        with self._read_pool_lock:
            if (read_pool := self._read_pool) is not None:
                read_pool.put(reader)
                return
        reader.close()  # the pool was closed while this reader was borrowed

    @contextmanager
    def read_ctx(self) -> Generator['DBCursor', None, None]:
        if (
                (read_pool := self._read_pool) is None or
                self.write_task_ident == (current_id := threading.get_ident()) or
                self.savepoint_task_ident == current_id
        ):
            # No pool, or this task holds the write transaction/savepoint stack and
            # must keep seeing its own uncommitted data: read on this connection.
            cursor = self.cursor()
            try:
                yield cursor
            finally:
                cursor.close()
            return

        if (reader := getattr(self._borrowed_reader, 'reader', None)) is not None:
            # nested read_ctx: reuse this thread's borrowed reader via a new cursor
            with reader.read_ctx() as cursor:
                yield cursor
            return

        reader = self._borrow_reader(read_pool)
        self._borrowed_reader.reader = reader
        try:
            with reader.read_ctx() as cursor:
                yield cursor
        finally:
            self._borrowed_reader.reader = None
            self._return_reader(reader)

    def _acquire_transaction_lock(self) -> None:
        """Blocking acquire of the transaction slot that stays responsive to task
        cancellation. The slot serializes write transactions and savepoint stacks
        of different tasks against each other, replacing the previous poll-a-field
        wait loops whose check-then-act windows were only race-free thanks to
        cooperative gevent scheduling.

        May raise TaskCancelledError.
        """
        while not self.transaction_lock.acquire(timeout=CONTEXT_SWITCH_WAIT):
            checkpoint()  # cancelled tasks should not keep waiting for the DB

    @contextmanager
    def write_ctx(self, commit_ts: bool = False) -> Generator['DBCursor', None, None]:
        """Opens a transaction to the database. This should be used kept open for
        as little time as possible.

        It's possible that a write transaction tries to be opened when savepoints are being used.
        In order for savepoints to work then, we will need to open a savepoint instead of a write
        transaction in that case. This should be used sparingly.
        """
        current_id = threading.get_ident()
        if (
                (self._conn.in_transaction is True and self.write_task_ident == current_id) or
                self.savepoint_task_ident == current_id
        ):  # this task already owns the transaction slot: nest via a savepoint
            with self.savepoint_ctx() as cursor:
                yield cursor
                return

        with self._transaction_slot(), self.critical_section():
            cursor = self.cursor()
            self.write_task_ident = current_id
            cursor.execute('BEGIN TRANSACTION')
            try:
                yield cursor
            except BaseException:  # also TaskCancelledError must roll back
                with self.statement_lock:
                    self._conn.rollback()
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
                with self.statement_lock:
                    self._conn.commit()
            finally:
                cursor.close()
                self.write_task_ident = None

    @contextmanager
    def savepoint_ctx(
            self,
            savepoint_name: str | None = None,
    ) -> Generator['DBCursor', None, None]:
        """
        Creates a savepoint context with the provided name. If the code inside the savepoint fails,
        rolls back this savepoint, otherwise releases it (aka forgets it -- this is not committed to the DB).
        Savepoints work like nested transactions, more information here: https://www.sqlite.org/lang_savepoint.html
        """    # noqa: E501
        cursor, savepoint_name = self._enter_savepoint(savepoint_name)
        try:
            yield cursor
        except BaseException:  # also TaskCancelledError/GreenletExit must roll back
            self.rollback_savepoint(savepoint_name)
            raise
        finally:
            self.release_savepoint(savepoint_name)
            cursor.close()

    def _enter_savepoint(self, savepoint_name: str | None = None) -> tuple['DBCursor', str]:
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

        checkpoint()  # a cancelled task should not open new savepoints
        current_id = threading.get_ident()
        if (
                (self._conn.in_transaction is True and self.write_task_ident == current_id) or
                self.savepoint_task_ident == current_id
        ):  # nesting inside this task's own write transaction or savepoint stack
            if savepoint_name in self.savepoints:
                raise ContextError(
                    f'Wanted to enter savepoint {savepoint_name} but a savepoint with the same '
                    f'name already exists. Current savepoints: {list(self.savepoints)}',
                )
        else:  # claim the transaction slot, waiting for other writers/savepoint stacks.
            # The previous holder always leaves an empty savepoint stack, so no
            # duplicate-name check is needed on this path.
            self._acquire_transaction_lock()
            self._savepoint_holds_transaction_lock = True

        try:
            cursor = self.cursor()
            cursor.execute(f"SAVEPOINT '{savepoint_name}'")
        except BaseException:
            if len(self.savepoints) == 0 and self._savepoint_holds_transaction_lock is True:
                self._savepoint_holds_transaction_lock = False
                self.transaction_lock.release()
            raise

        self.savepoints[savepoint_name] = None
        self.savepoint_task_ident = current_id
        return cursor, savepoint_name

    def _modify_savepoint(
            self,
            rollback_or_release: Literal['ROLLBACK TO', 'RELEASE'],
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

        # Hold in_callback so the progress callback exits immediately: no context
        # switches and no cancellation aborts while modifying savepoint state, since
        # this also runs during cleanup of an already-cancelled task.
        with self.in_callback, self.cursor() as cursor:  # this should not be a write_ctx as it's inside savepoint logic and would block  # noqa: E501
            cursor.execute(f"{rollback_or_release} SAVEPOINT '{savepoint_name}'")

        # Release all savepoints until, and including, the one with name `savepoint_name`.
        # For rollback we don't remove the savepoints since they are not released yet.
        if rollback_or_release == 'RELEASE':
            self.savepoints = dict.fromkeys(list_savepoints[:list_savepoints.index(savepoint_name)])  # noqa: E501
            if len(self.savepoints) == 0:  # we are out of all savepoints
                self.savepoint_task_ident = None
                if self._savepoint_holds_transaction_lock is True:  # free the transaction slot
                    self._savepoint_holds_transaction_lock = False
                    self.transaction_lock.release()

    def rollback_savepoint(self, savepoint_name: str | None = None) -> None:
        """
        Rollbacks to `savepoint_name` if given and to the latest savepoint otherwise.
        May raise:
        - ContextError if savepoints stack is empty or given savepoint name is not in the stack
        """
        self._modify_savepoint(rollback_or_release='ROLLBACK TO', savepoint_name=savepoint_name)

    def release_savepoint(self, savepoint_name: str | None = None) -> None:
        """
        Releases (aka forgets) `savepoint_name` if given and the latest savepoint otherwise.
        May raise:
        - ContextError if savepoints stack is empty or given savepoint name is not in the stack
        """
        self._modify_savepoint(rollback_or_release='RELEASE', savepoint_name=savepoint_name)

    @contextmanager
    def critical_section(self) -> Generator[None, None, None]:
        """Disable the progress callback's effects for the duration of the context.

        The sqlite progress handler must NOT be toggled here:
        set_progress_handler() blocks on sqlite's connection mutex while holding
        the GIL, and another thread mid-statement holds that mutex while its
        progress callback waits for the GIL -- a deadlock. Holding
        in_critical_section is enough, since the callback exits immediately
        (without aborting cancelled statements) while it is locked.
        """
        with self.in_critical_section:
            if __debug__:
                identifier = random.random()
                logger.trace(f'Got in critical section for {self.connection_type} and id: {identifier}')  # noqa: E501

            with self.in_callback:
                if __debug__:
                    logger.trace(f'entering critical section for {self.connection_type} and id: {identifier}')  # noqa: E501  # pyright: ignore  # if debug identifier is set
            try:
                yield
            finally:
                with self.in_callback:
                    if __debug__:
                        logger.trace(f'exiting critical section for {self.connection_type} and id {identifier}')  # noqa: E501  # pyright: ignore  # if debug identifier is set

    @contextmanager
    def _transaction_slot(self) -> Generator[None, None, None]:
        """Holds the transaction slot for the duration of the context.

        Always acquire the slot BEFORE entering a critical section: write_ctx does the
        same, so any other ordering would create a deadlock cycle between the two locks.
        """
        self._acquire_transaction_lock()
        try:
            yield
        finally:
            self.transaction_lock.release()

    @contextmanager
    def critical_section_and_transaction_lock(self) -> Generator[None, None, None]:
        with self._transaction_slot(), self.critical_section():
            yield

    def vacuum(self) -> None:
        """Helper function to vacuum the DB. Abstracted into its own function since
        incorrect usage of the PRAGMA can result in errors. For example should not do it
        while there is an open transaction"""
        with self._transaction_slot(), self.critical_section():  # make sure no writing happens while vacuuming  # noqa: E501
            cursor = self.cursor()
            cursor.execute('VACUUM')
            cursor.close()

    def wal_checkpoint(self, mode: Literal['', '(FULL)', '(PASSIVE)', '(TRUNCATE)'] = '') -> None:
        """
        Perform a WAL checkpoint operation.
        https://www.sqlite.org/pragma.html#pragma_wal_checkpoint
        Made as part of the connection to control how it's made. Cursors should
        not execute this if there an open transaction with pending changes as it can
        also result in database table is locked.

        Args:
            mode: Optional checkpoint mode ('PASSIVE', 'FULL', 'RESTART', 'TRUNCATE').
                 If '', uses default (PASSIVE).

        This method acquires the callback lock to prevent progress callbacks from
        interfering with the checkpoint operation, which can cause 'database table is locked'
        errors due to context switches during the checkpoint. See issue #5038 for details.

        A concurrent reader on this connection whose statement is still active
        (started but not exhausted/reset) also makes the checkpoint raise
        'database table is locked'. Statement-active windows are short and a
        checkpoint is opportunistic (sqlite auto-checkpoints and flushes at
        close), so retry for a bit and give up with a warning instead of
        raising -- must-succeed callers (DB upgrades) run without concurrency
        and succeed on the first try.
        """
        pragma_sql = f'PRAGMA wal_checkpoint{mode};'
        # Acquire the callback lock to prevent progress callbacks from causing
        # context switches during the checkpoint operation
        deadline = time.monotonic() + 2
        with self.in_callback:
            if __debug__:
                logger.trace(f'START {pragma_sql}')

            with self.cursor() as cursor:
                while True:
                    try:
                        result = cursor.execute(pragma_sql).fetchone()
                    except (sqlcipher.OperationalError, rsqlite.OperationalError) as e:  # pylint: disable=no-member
                        if 'locked' not in str(e):
                            raise
                        if time.monotonic() >= deadline:
                            logger.warning(
                                'Skipped %s since a reader kept a statement '
                                'active during all attempts. The WAL file stays until '
                                'a later checkpoint.',
                                pragma_sql,
                            )
                            return
                        time.sleep(0.05)  # a reader mid-statement: let it finish
                        continue
                    break

                if __debug__:
                    if len(result) != 3:  # should never happen, PRAGMA wal checkpoint returns 3 ints # noqa: E501
                        result_text = ''
                    else:
                        result_text = f' with result(Status: {result[0]}, Wal file Pages: {result[1]}, Checkpointed Pages: {result[2]})'  # noqa: E501

                    logger.trace(f'FINISH {pragma_sql}{result_text}')

    @property
    def total_changes(self) -> int:
        """total number of database rows that have been modified, inserted,
        or deleted since the database connection was opened"""
        with self.statement_lock:
            return self._conn.total_changes

    def schema_sanity_check(self) -> None:
        """Ensures that database schema is not broken.

        If you need to regenerate the schema that is being checked run:
        tools/scripts/generate_minimized_db_schema.py

        Raises DBSchemaError if anything is off.
        """
        assert (
            self.connection_type != DBConnectionType.TRANSIENT and
            self.minimized_schema is not None and
            self.minimized_indexes is not None
        )

        with self.read_ctx() as cursor:
            sanity_check_impl(
                cursor=cursor,
                db_name=self.connection_type.name.lower(),
                minimized_schema=self.minimized_schema,
                minimized_indexes=self.minimized_indexes,
            )
