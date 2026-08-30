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
from collections import deque
from contextlib import contextmanager, suppress
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Self
from uuid import uuid4
from weakref import WeakSet

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
    from collections.abc import Callable, Generator, Sequence
    from types import TracebackType

    from rotkehlchen.logging import RotkehlchenLogger

type UnderlyingCursor = rsqlite.Cursor | sqlcipher.Cursor  # pylint: disable=no-member
type UnderlyingConnection = rsqlite.Connection | sqlcipher.Connection  # pylint: disable=no-member

CONTEXT_SWITCH_WAIT = 0.025  # seconds between cancellation checks while waiting for the transaction slot  # noqa: E501
# Rows a cursor prefetches per statement_lock acquisition when iterated. Iteration
# is the hot row-consumption path (~1650 call sites): taking the lock per row costs
# 2.3x uncontended and up to 14x with another thread using the same connection
# (measured), so fetch in batches under one hold. 1000 rows keeps the buffer's
# memory footprint trivial while making the per-row lock cost disappear.
CURSOR_PREFETCH_ROWS = 1000
# How long disable_read_pool() waits for borrowed readers to be returned before
# interrupting their in-flight statements. Read contexts are short (statement
# duration), so this is generous; matching DEFAULT_CANCEL_GRACE_SECONDS in spirit.
DISABLE_READ_POOL_DRAIN_SECONDS = 3.0
# Extra wait after interrupting the statements of still-borrowed readers, for
# their read contexts to unwind and return them.
DISABLE_READ_POOL_INTERRUPT_GRACE_SECONDS = 1.0

logger: RotkehlchenLogger = logging.getLogger(__name__)  # type: ignore


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

    def __init__(self, connection: DBConnection, cursor: UnderlyingCursor) -> None:
        self._cursor = cursor
        self.connection = connection
        # Rows prefetched by __next__ and not yet consumed. Emptied by execute*()
        # (a new statement discards the previous result set, as the underlying
        # cursor does) and drained first by the fetch*() methods so that mixing
        # iteration with fetch calls keeps the underlying cursor's semantics.
        self._prefetched_rows: deque[Any] = deque()

    def __iter__(self) -> DBCursor:
        if __debug__:
            logger.trace(f'Getting iterator for cursor {id(self)}')
        return self

    def __next__(self) -> Any:
        """
        We type this and other function returning Any since anything else has
        too many false positives. Same as typeshed:
        https://github.com/python/typeshed/blob/a750a42c65b77963ff097b6cbb6d36cef5912eb7/stdlib/sqlite3/dbapi2.pyi#L397
        """
        if len(self._prefetched_rows) == 0:
            try:
                with self.connection.statement_lock:
                    if __debug__:
                        logger.trace(f'Prefetching up to {CURSOR_PREFETCH_ROWS} rows for cursor {id(self)}')  # noqa: E501
                    self._prefetched_rows.extend(self._cursor.fetchmany(CURSOR_PREFETCH_ROWS))
            except (sqlcipher.OperationalError, rsqlite.OperationalError) as e:  # pylint: disable=no-member
                _maybe_raise_cancelled(e)
                raise
            if len(self._prefetched_rows) == 0:
                if __debug__:
                    logger.trace(f'Stopping iteration for cursor {id(self)}')
                raise StopIteration

        return self._prefetched_rows.popleft()

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

    def execute(self, statement: str, *bindings: Sequence) -> DBCursor:
        if __debug__:
            logger.trace(f'EXECUTE {statement} with bindings {bindings} for cursor {id(self)}')
        self._prefetched_rows.clear()  # a new statement discards the previous result set
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
            *bindings: Sequence[Sequence] | Generator[Sequence],
    ) -> DBCursor:
        if __debug__:
            logger.trace(f'EXECUTEMANY {statement} with bindings {bindings} for cursor {id(self)}')
        self._prefetched_rows.clear()  # a new statement discards the previous result set
        try:
            with self.connection.statement_lock:
                self._cursor.executemany(statement, *bindings)
        except (sqlcipher.OperationalError, rsqlite.OperationalError) as e:  # pylint: disable=no-member
            _maybe_raise_cancelled(e)
            raise
        if __debug__:
            logger.trace(f'FINISH EXECUTEMANY {statement} with bindings {bindings} for cursor {id(self)}')  # noqa: E501
        return self

    def executescript(self, script: str) -> DBCursor:
        """Remember this always issues a COMMIT before
        https://docs.python.org/3/library/sqlite3.html#sqlite3.Cursor.executescript
        """
        if __debug__:
            logger.trace(f'EXECUTESCRIPT {script} for cursor {id(self)}')
        self._prefetched_rows.clear()  # a new statement discards the previous result set
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
        if len(self._prefetched_rows) != 0:
            return self._prefetched_rows.popleft()
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
        if size <= 0:
            # both underlying drivers treat a non-positive size as "no limit" and
            # return all remaining rows -- mirror that instead of returning []
            return self.fetchall()
        result: list[Any] = []
        while len(result) < size and len(self._prefetched_rows) != 0:
            result.append(self._prefetched_rows.popleft())
        if len(result) == size:
            return result
        try:
            with self.connection.statement_lock:
                result.extend(self._cursor.fetchmany(size - len(result)))
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
        if len(self._prefetched_rows) != 0:  # prefetched rows precede the remainder
            result = list(self._prefetched_rows) + result
            self._prefetched_rows.clear()
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
        self._prefetched_rows.clear()
        with self.connection.statement_lock:
            try:
                self._cursor.close()
            finally:
                self.connection._cursors.discard(self)


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
CONNECTION_MAP: dict[DBConnectionType, DBConnection] = {}


def _progress_callback(connection: DBConnection | None) -> int:
    """Needs to be a static function. Cannot be a connection class method
    or sqlite breaks in funny ways. Raises random Operational errors.
    """
    if connection is None:
        return 0

    if (
            connection.in_callback.locked() or
            connection.critical_section_owner == threading.get_ident()
    ):
        # if we get here and the connection is locked or THIS thread is inside a
        # critical section, its state must not be modified nor its running statement
        # aborted from within the callback (e.g. a commit is in progress). So we
        # immediately exit the callback without doing anything. Ownership matters
        # for the critical section check: another thread's critical section (e.g. a
        # long write transaction) protects only that thread's statements, and must
        # not suppress the cancellation of every other task's statements with it.
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
        self._cursors: WeakSet[DBCursor] = WeakSet()
        # Pool of read-only connections configured by enable_read_pool() and created
        # lazily as concurrent reads need them. LIFO reuse keeps sequential reads on
        # the same warm SQLite page cache instead of rotating through every reader.
        # While None, read_ctx() serves cursors of this (the write) connection.
        self._read_pool: queue.LifoQueue[DBConnection] | None = None
        self._read_pool_lock = threading.Lock()
        self._read_pool_size = 0
        self._readers_num = 0
        self._reader_setup: Callable[[DBConnection], None] | None = None
        # Number of readers currently borrowed (or being borrowed) from the pool,
        # so disable_read_pool() can wait for them: callers disable the pool to
        # delete or re-key the underlying file, and a still-open borrowed reader
        # would make the unlink fail on windows or read re-keyed pages as garbage.
        self._borrowed_readers_count = 0
        self._readers_returned = threading.Condition(self._read_pool_lock)
        # The borrowed reader connections themselves (guarded by the same lock),
        # so disable_read_pool() can interrupt their in-flight statements once
        # its graceful wait for their return expires.
        self._borrowed_readers: set[DBConnection] = set()
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
        # ident of the thread currently inside critical_section(), so the progress
        # callback can suppress cancellation aborts for that thread's statements
        # only instead of for every thread on the connection
        self.critical_section_owner: int | None = None
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
        elif read_only:
            # as_uri() gives a percent-encoded file:// URI that sqlite accepts
            # on all platforms (a plain f'file:{path}' breaks on windows paths).
            # The caller must key the connection (PRAGMA key) before reading.
            self._conn = sqlcipher.connect(  # pylint: disable=no-member
                database=Path(path).absolute().as_uri() + '?mode=ro',
                uri=True,
                check_same_thread=False,
                isolation_level=None,
            )
        else:
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
            cursor = DBCursor(connection=self, cursor=self._conn.cursor())
            self._cursors.add(cursor)
            return cursor

    def interrupt(self) -> None:
        """Abort this connection's in-flight statements (sqlite3_interrupt). Safe
        to call from any thread and without the statement lock, which the thread
        running the statement to be aborted is holding."""
        self._conn.interrupt()

    def close(self) -> None:
        self.disable_read_pool()
        with self.statement_lock:
            for cursor in tuple(self._cursors):
                cursor.close()
            self._conn.close()
        if not self._read_only:  # a reader was never registered in the map
            CONNECTION_MAP.pop(self.connection_type, None)

    def enable_read_pool(
            self,
            size: int = 4,
            reader_setup: Callable[[DBConnection], None] | None = None,
    ) -> None:
        """Configure the pool of read-only connections that read_ctx() borrows from.

        Must only be called after the database is in WAL mode: with the default
        journal mode a writer's transaction blocks readers on other connections
        (and vice versa), while under WAL they proceed concurrently and each read
        statement sees a consistent committed snapshot.

        Readers are created lazily up to size as concurrent reads require them.
        reader_setup runs once per created reader, for connection-level preparation
        reads need -- keying sqlcipher readers (PRAGMA key) most importantly.
        Persistent database errors disable the pool; transient errors release the
        reader reservation so a later read can retry.

        No-op for in-memory databases (used by tests): they cannot use WAL and
        there is no file for a second connection to open, so read_ctx() keeps
        serving cursors of this connection there.
        """
        assert self._read_only is False, 'cannot enable a read pool on a pool reader'
        assert size > 0, 'read pool size must be positive'
        if str(self._path) == ':memory:':
            return
        with self._read_pool_lock:
            if self._read_pool is not None:
                return  # already enabled -- happens when connect-time actions rerun
            self._read_pool = queue.LifoQueue()
            self._read_pool_size = size
            self._reader_setup = reader_setup

    def disable_read_pool(self) -> None:
        """Close the pooled readers and make read_ctx() serve cursors of this
        connection again. No-op if no pool is enabled.

        Waits (bounded) for borrowed readers to be returned first: callers
        disable the pool to delete or re-key the underlying file, and a reader
        still open at that moment makes the file unlink fail on windows
        (premium sync pull) or serves re-keyed pages as garbage. A reader not
        returned within the wait gets its in-flight statements interrupted so
        its read context errors out and returns it; one still not returned
        after that is closed by _return_reader when its read_ctx exits, since
        the pool it would be returned to is gone.
        """
        with self._readers_returned:
            read_pool, self._read_pool = self._read_pool, None
            self._read_pool_size = 0
            self._readers_num = 0
            self._reader_setup = None
            if read_pool is None:
                return
            deadline = time.monotonic() + DISABLE_READ_POOL_DRAIN_SECONDS
            interrupted = False
            while self._borrowed_readers_count > 0:
                if (remaining := deadline - time.monotonic()) <= 0:
                    if interrupted:
                        logger.warning(
                            'Disabling the read pool with %s readers still borrowed '
                            'after interrupting their statements. The operation that '
                            'needed the pool gone may fail.',
                            self._borrowed_readers_count,
                        )
                        break
                    # the graceful wait expired: abort the borrowed readers'
                    # in-flight statements so their read contexts exit, then
                    # wait (bounded again) for them to be returned
                    for reader in self._borrowed_readers:
                        reader.interrupt()
                    interrupted = True
                    deadline = time.monotonic() + DISABLE_READ_POOL_INTERRUPT_GRACE_SECONDS
                    continue
                self._readers_returned.wait(remaining)
        self._close_idle_readers(read_pool)

    @staticmethod
    def _close_idle_readers(read_pool: queue.LifoQueue[DBConnection]) -> None:
        """Detach and close all readers that are currently idle in the pool."""
        with read_pool.mutex:
            readers = list(read_pool.queue)
            read_pool.queue.clear()
        for reader in readers:
            reader.close()

    def _create_reader(
            self,
            reader_setup: Callable[[DBConnection], None] | None,
    ) -> DBConnection:
        """Create and prepare one read-only connection for the pool."""
        reader = DBConnection(
            path=self._path,
            connection_type=self.connection_type,
            sql_vm_instructions_cb=self.sql_vm_instructions_cb,
            read_only=True,
        )
        try:
            if reader_setup is not None:
                reader_setup(reader)
        except BaseException:
            reader.close()
            raise
        return reader

    def _borrow_reader(
            self,
            read_pool: queue.LifoQueue[DBConnection],
    ) -> DBConnection | None:
        """Borrow an idle reader, lazily creating one while below the pool limit.

        If all readers are borrowed, wait while staying responsive to task
        cancellation, mirroring _acquire_transaction_lock. Returns None if the
        pool is disabled concurrently, so read_ctx can fall back to the write
        connection.

        May raise TaskCancelledError.
        """
        while True:
            with suppress(queue.Empty):
                reader = read_pool.get_nowait()
                with self._read_pool_lock:
                    if self._read_pool is read_pool:
                        return reader
                reader.close()
                return None

            with self._read_pool_lock:
                if self._read_pool is not read_pool:
                    return None
                with suppress(queue.Empty):  # may have been returned before we got the lock
                    return read_pool.get_nowait()
                if self._readers_num < self._read_pool_size:
                    self._readers_num += 1  # reserve capacity before creating outside the lock
                    reader_setup = self._reader_setup
                    break

            try:
                return read_pool.get(timeout=CONTEXT_SWITCH_WAIT)
            except queue.Empty:
                checkpoint()  # cancelled tasks should not keep waiting for a reader
                if self._read_pool is not read_pool:
                    return None  # the pool was disabled while waiting

        try:
            reader = self._create_reader(reader_setup)
        except BaseException as e:
            persistent_error = isinstance(  # pylint: disable=no-member
                e,
                (sqlcipher.DatabaseError, rsqlite.Error),
            )
            with self._read_pool_lock:
                if self._read_pool is read_pool:
                    if persistent_error:
                        self._read_pool = None
                        self._read_pool_size = 0
                        self._readers_num = 0
                        self._reader_setup = None
                    else:
                        self._readers_num -= 1
            if persistent_error:
                self._close_idle_readers(read_pool)
            raise

        with self._read_pool_lock:
            if self._read_pool is read_pool:
                return reader
        reader.close()  # the pool was disabled while this reader was being prepared
        return None

    def _return_reader(
            self,
            reader: DBConnection,
            source_pool: queue.LifoQueue[DBConnection],
    ) -> None:
        with self._readers_returned:
            self._borrowed_readers_count -= 1
            self._borrowed_readers.discard(reader)
            self._readers_returned.notify_all()
            if self._read_pool is source_pool:
                source_pool.put(reader)
                return
        reader.close()  # its source pool was closed while this reader was borrowed

    @contextmanager
    def read_ctx(self) -> Generator[DBCursor]:
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

        # count the borrow before taking from the queue: a disable_read_pool that
        # runs between the take and the count increment would otherwise miss this
        # reader and proceed while it is still open
        with self._readers_returned:
            self._borrowed_readers_count += 1
        reader = None
        try:
            reader = self._borrow_reader(read_pool)
        finally:
            if reader is None:  # cancelled, or the pool got disabled while waiting
                with self._readers_returned:
                    self._borrowed_readers_count -= 1
                    self._readers_returned.notify_all()

        if reader is None:
            # The pool was disabled after read_ctx observed it. Fall back to the
            # write connection just as a read starting after disable_read_pool does.
            cursor = self.cursor()
            try:
                yield cursor
            finally:
                cursor.close()
            return

        with self._readers_returned:
            self._borrowed_readers.add(reader)
        self._borrowed_reader.reader = reader
        try:
            with reader.read_ctx() as cursor:
                yield cursor
        finally:
            self._borrowed_reader.reader = None
            self._return_reader(reader, read_pool)

    def _acquire_transaction_lock(self) -> None:
        """Blocking acquire of the transaction slot that stays responsive to task
        cancellation. The slot serializes write transactions and savepoint stacks
        of different tasks against each other, replacing the previous poll-a-field
        wait loops whose check-then-act windows were only race-free thanks to
        cooperative gevent scheduling.

        May raise TaskCancelledError.
        """
        if __debug__:
            # lock-order check: the transaction slot must be taken BEFORE entering a
            # critical section (see _transaction_slot docstring) -- the reverse order
            # creates a deadlock cycle against write_ctx, which takes slot-then-section
            assert self.critical_section_owner != threading.get_ident(), (
                'attempted to acquire the transaction slot while inside a critical section'
            )
        while not self.transaction_lock.acquire(timeout=CONTEXT_SWITCH_WAIT):
            checkpoint()  # cancelled tasks should not keep waiting for the DB

    @contextmanager
    def write_ctx(self, commit_ts: bool = False) -> Generator[DBCursor]:
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
    ) -> Generator[DBCursor]:
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

    def _enter_savepoint(self, savepoint_name: str | None = None) -> tuple[DBCursor, str]:
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

        try:
            # Hold in_callback so the progress callback exits immediately: no context
            # switches and no cancellation aborts while modifying savepoint state, since
            # this also runs during cleanup of an already-cancelled task.
            with self.in_callback, self.cursor() as cursor:  # this should not be a write_ctx as it's inside savepoint logic and would block  # noqa: E501
                cursor.execute(f"{rollback_or_release} SAVEPOINT '{savepoint_name}'")
        finally:
            # Release all savepoints until, and including, the one with name
            # `savepoint_name`. For rollback we don't remove the savepoints since they
            # are not released yet. The bookkeeping runs even when the statement fails
            # (e.g. an executescript inside the savepoint body issued an implicit
            # COMMIT that destroyed all sqlite savepoints, making the RELEASE raise
            # 'no such savepoint'): abandoning the stack is strictly safer than
            # leaking the transaction slot, which on the process-lifetime global
            # connection would block every global write until restart.
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
    def critical_section(self) -> Generator[None]:
        """Disable the progress callback's effects for the duration of the context.

        The sqlite progress handler must NOT be toggled here:
        set_progress_handler() blocks on sqlite's connection mutex while holding
        the GIL, and another thread mid-statement holds that mutex while its
        progress callback waits for the GIL -- a deadlock. Holding
        in_critical_section is enough, since the callback exits immediately
        (without aborting cancelled statements) while it is locked.
        """
        with self.in_critical_section:
            self.critical_section_owner = threading.get_ident()
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
                self.critical_section_owner = None

    @contextmanager
    def _transaction_slot(self) -> Generator[None]:
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
    def critical_section_and_transaction_lock(
            self,
            cancellable: bool = True,
    ) -> Generator[None]:
        """Hold the transaction slot and a critical section, in that order (the
        reverse creates a deadlock cycle against write_ctx).

        With cancellable=False the slot is taken with a plain blocking acquire
        containing no cancellation checkpoints: for cleanup paths (e.g. detaching
        an attached database) that must run even inside an already-cancelled task,
        where the checkpoint of the normal acquire loop would raise before the
        cleanup statement could execute.
        """
        if cancellable:
            with self._transaction_slot(), self.critical_section():
                yield
            return

        if __debug__:  # same lock-order check as _acquire_transaction_lock
            assert self.critical_section_owner != threading.get_ident(), (
                'attempted to acquire the transaction slot while inside a critical section'
            )
        self.transaction_lock.acquire()
        try:
            with self.critical_section():
                yield
        finally:
            self.transaction_lock.release()

    def vacuum(self) -> None:
        """Helper function to vacuum the DB. Abstracted into its own function since
        incorrect usage of the PRAGMA can result in errors. For example should not do it
        while there is an open transaction"""
        with self._transaction_slot(), self.critical_section():  # make sure no writing happens while vacuuming  # noqa: E501
            cursor = self.cursor()
            cursor.execute('VACUUM')
            cursor.close()

    def vacuum_into(self, target: Path) -> None:
        """Write a consistent, defragmented snapshot of the database to target via
        VACUUM INTO. Unlike checkpoint-then-copy the snapshot always contains all
        committed data (a PASSIVE checkpoint stops at the oldest pooled reader's
        snapshot) and cannot be torn by concurrent commits rewriting pages mid-copy.
        On an encrypted database the snapshot is encrypted with the same key.

        Holds the transaction slot since VACUUM cannot run within a transaction.
        A partial target file is removed on failure.

        May raise sqlcipher/rsqlite errors (existing target, IO failure, ...).
        """
        with self._transaction_slot(), self.critical_section():
            try:
                with self.cursor() as cursor:
                    cursor.execute('VACUUM INTO ?', (str(target),))
            except BaseException:  # also cancellation must not leave a partial file
                target.unlink(missing_ok=True)
                raise

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
        deadline = time.monotonic() + 2
        while True:
            # Acquire the callback lock per attempt -- NOT across the retry sleep:
            # commit/rollback and the savepoint bookkeeping block on in_callback,
            # so holding it for the whole retry window would stall every write on
            # the connection while a reader keeps a statement active. Holding it
            # around the attempt itself prevents progress callbacks from causing
            # context switches during the checkpoint operation (see issue #5038).
            with self.in_callback:
                if __debug__:
                    logger.trace(f'START {pragma_sql}')
                try:
                    with self.cursor() as cursor:
                        result = cursor.execute(pragma_sql).fetchone()
                except (sqlcipher.OperationalError, rsqlite.OperationalError) as e:  # pylint: disable=no-member
                    if 'locked' not in str(e):
                        raise
                    result = None

            if result is not None:
                break
            if time.monotonic() >= deadline:
                logger.warning(
                    'Skipped %s since a reader kept a statement '
                    'active during all attempts. The WAL file stays until '
                    'a later checkpoint.',
                    pragma_sql,
                )
                return
            time.sleep(0.05)  # a reader mid-statement: let it finish

        if __debug__:
            if len(result) != 3:  # should never happen, PRAGMA wal checkpoint returns 3 ints
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
