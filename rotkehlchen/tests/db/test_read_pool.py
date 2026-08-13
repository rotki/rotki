"""Tests for the pool of read-only connections that isolates read_ctx() readers
from write commits on the same DB (WAL mode). See DBConnection.enable_read_pool.
"""
import threading
import time
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Final
from unittest.mock import Mock

import pytest
import rsqlite
from sqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.concurrency import Task, TaskCancelledError, spawn, wait
from rotkehlchen.db.drivers.sqlite import DBConnection, DBConnectionType
from rotkehlchen.db.utils import unlock_database

if TYPE_CHECKING:
    from pathlib import Path

POOL_SIZE: Final = 2
USER_DB_PASSWORD: Final = '123'


@pytest.fixture(name='conn')
def fixture_conn(tmp_path: Path) -> Any:
    """A file-backed WAL-mode global-type connection with the read pool enabled,
    mirroring how configure_globaldb sets up the real global DB connection"""
    conn = DBConnection(
        path=tmp_path / 'test.db',
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=100,
    )
    with conn.write_ctx() as cursor:
        cursor.executescript('PRAGMA journal_mode=WAL;')
    with conn.write_ctx() as cursor:
        cursor.execute('CREATE TABLE t(id INTEGER PRIMARY KEY AUTOINCREMENT, a INTEGER)')
        cursor.execute('INSERT INTO t(a) VALUES (1)')
    conn.enable_read_pool(size=POOL_SIZE)
    yield conn
    conn.close()


def test_write_through_read_cursor_raises(conn: DBConnection) -> None:
    """Pooled readers are opened with mode=ro so a write through read_ctx fails loudly"""
    with conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM t').fetchone() == (1,)
        with pytest.raises(rsqlite.OperationalError, match='readonly'):
            cursor.execute('INSERT INTO t(a) VALUES (2)')


def test_read_pool_grows_lazily_and_reuses_last_reader(conn: DBConnection) -> None:
    """Enabling the pool opens nothing until needed, grows only with concurrent
    demand and keeps sequential reads on the most recently used warm connection."""
    assert conn._readers_num == 0
    assert (read_pool := conn._read_pool) is not None

    with conn.read_ctx():
        first_reader = conn._borrowed_reader.reader
    assert conn._readers_num == 1

    borrowed_first = conn._borrow_reader(read_pool)
    borrowed_second = conn._borrow_reader(read_pool)
    assert borrowed_first is first_reader
    assert borrowed_first is not None
    assert borrowed_second is not None
    assert conn._readers_num == POOL_SIZE
    conn._return_reader(borrowed_first, read_pool)
    conn._return_reader(borrowed_second, read_pool)

    with conn.read_ctx():
        assert conn._borrowed_reader.reader is borrowed_second


def test_transient_reader_setup_failure_keeps_pool_enabled(conn: DBConnection) -> None:
    """Cancellation during lazy setup releases the reserved slot and lets a later read retry."""
    conn.disable_read_pool()
    reader_setup = Mock(side_effect=(TaskCancelledError('cancelled'), None))
    conn.enable_read_pool(size=1, reader_setup=reader_setup)
    read_pool = conn._read_pool

    with pytest.raises(TaskCancelledError), conn.read_ctx():
        pass
    assert conn._read_pool is read_pool
    assert conn._readers_num == 0

    with conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM t').fetchone() == (1,)
    assert conn._readers_num == 1
    assert reader_setup.call_count == 2


def test_own_uncommitted_data_stays_visible(conn: DBConnection) -> None:
    """The thread holding the write transaction or savepoint stack must keep
    reading its own uncommitted data, so its read_ctx uses the write connection"""
    with conn.write_ctx() as write_cursor:
        write_cursor.execute('INSERT INTO t(a) VALUES (2)')
        with conn.read_ctx() as cursor:
            assert cursor.execute('SELECT COUNT(*) FROM t').fetchone() == (2,)

    with conn.savepoint_ctx() as savepoint_cursor:
        savepoint_cursor.execute('INSERT INTO t(a) VALUES (3)')
        with conn.read_ctx() as cursor:
            assert cursor.execute('SELECT COUNT(*) FROM t').fetchone() == (3,)


def test_readers_are_isolated_from_write_commits(conn: DBConnection) -> None:
    """The reason the pool exists: another thread's commit must neither reset an
    in-flight read statement nor leak uncommitted data into it"""
    with conn.write_ctx() as write_cursor:
        write_cursor.executemany('INSERT INTO t(a) VALUES (?)', [(i,) for i in range(2, 11)])

    read_results: list[int] = []
    reader_started = threading.Event()

    def slow_reader() -> None:
        with conn.read_ctx() as cursor:
            cursor.execute('SELECT a FROM t')
            reader_started.set()
            for _ in cursor:  # keep the statement active across the writer's commits
                read_results.append(1)
                time.sleep(0.01)

    def writer() -> None:
        assert reader_started.wait(timeout=5)
        for i in range(5):
            with conn.write_ctx() as write_cursor:
                write_cursor.execute('INSERT INTO t(a) VALUES (?)', (100 + i,))
            time.sleep(0.01)

    tasks: list[Task] = [spawn(slow_reader), spawn(writer)]
    wait(tasks)
    assert [task.exception for task in tasks] == [None, None]
    # the reader's snapshot had exactly the 10 rows committed before it started
    assert len(read_results) == 10

    # a fresh statement on a pooled reader sees the writer's committed rows
    with conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM t').fetchone() == (15,)


def test_uncommitted_data_invisible_to_other_threads(conn: DBConnection) -> None:
    """A pooled reader on another thread sees only committed data while a write
    transaction is open"""
    seen_count = 0

    def other_reader() -> None:
        nonlocal seen_count
        with conn.read_ctx() as cursor:
            seen_count = cursor.execute('SELECT COUNT(*) FROM t').fetchone()[0]

    with conn.write_ctx() as write_cursor:
        write_cursor.execute('INSERT INTO t(a) VALUES (2)')
        wait([spawn(other_reader)])
    assert seen_count == 1


def test_nested_read_ctx_reuses_borrowed_reader(tmp_path: Path) -> None:
    """Nested read_ctx calls on one thread reuse the thread's borrowed reader.
    With a pool of one reader and several nesting threads this would otherwise
    deadlock, each thread holding a reader while waiting for another."""
    conn = DBConnection(
        path=tmp_path / 'test.db',
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=100,
    )
    with conn.write_ctx() as cursor:
        cursor.executescript('PRAGMA journal_mode=WAL;')
    with conn.write_ctx() as cursor:
        cursor.execute('CREATE TABLE t(a INTEGER)')
        cursor.execute('INSERT INTO t VALUES (1)')
    conn.enable_read_pool(size=1)

    def nesting_reader() -> None:
        for _ in range(10):
            with conn.read_ctx() as outer_cursor:
                outer_cursor.execute('SELECT COUNT(*) FROM t')
                with conn.read_ctx() as inner_cursor:
                    assert inner_cursor.execute('SELECT COUNT(*) FROM t').fetchone() == (1,)
                assert outer_cursor.fetchone() == (1,)

    tasks = [spawn(nesting_reader) for _ in range(4)]
    wait(tasks)
    assert [task.exception for task in tasks] == [None] * len(tasks)
    conn.close()


def test_enable_read_pool_is_noop_for_memory_db() -> None:
    """In-memory DBs (used by the globaldb test fixture) cannot use WAL and have
    no file to open read-only, so read_ctx keeps using the write connection"""
    conn = DBConnection(
        path=':memory:',
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=100,
    )
    conn.enable_read_pool()
    with conn.write_ctx() as cursor:
        cursor.execute('CREATE TABLE t(a INTEGER)')
    with conn.read_ctx() as cursor:  # a pooled ro reader would fail here
        cursor.execute('INSERT INTO t VALUES (1)')
    conn.close()


def test_close_with_borrowed_reader(conn: DBConnection) -> None:
    """Closing the connection while a reader is borrowed closes that reader when
    it is returned instead of leaking it"""
    with conn.read_ctx() as cursor:
        cursor.execute('SELECT COUNT(*) FROM t').fetchone()
        reader = conn._borrowed_reader.reader
        conn.close()
    # the read_ctx exit returned the reader to the closed pool, closing it
    with pytest.raises(rsqlite.ProgrammingError):
        reader.cursor()


def test_disable_read_pool_interrupts_borrowed_reader(
        conn: DBConnection,
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A reader still executing a statement when the drain wait expires gets it
    interrupted, so the disabling caller proceeds without a reader holding the
    file open instead of only logging a warning"""
    monkeypatch.setattr('rotkehlchen.db.drivers.sqlite.DISABLE_READ_POOL_DRAIN_SECONDS', 0.2)
    reading = threading.Event()
    borrowed: list[DBConnection] = []
    errors: list[Exception] = []

    def stuck_reader() -> None:
        with conn.read_ctx() as cursor:
            borrowed.append(conn._borrowed_reader.reader)
            reading.set()
            try:
                cursor.execute(
                    'WITH RECURSIVE c(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM c '
                    'WHERE x < 500000000) SELECT COUNT(*) FROM c',
                ).fetchone()
            except rsqlite.OperationalError as e:  # pylint: disable=no-member
                errors.append(e)

    task = spawn(stuck_reader)
    assert reading.wait(timeout=5)
    time.sleep(0.1)  # let the reader enter the statement before disabling
    try:
        conn.disable_read_pool()
    finally:  # if disabling failed to interrupt, don't leave the query running for minutes
        with suppress(rsqlite.ProgrammingError):  # closed already when disabling worked
            borrowed[0].interrupt()
    wait([task])
    assert task.exception is None
    assert conn._borrowed_readers_count == 0
    assert len(errors) == 1 and 'interrupted' in str(errors[0])
    with pytest.raises(rsqlite.ProgrammingError):  # returned to the gone pool and closed
        borrowed[0].cursor()


def test_borrowed_reader_is_not_returned_to_replacement_pool(conn: DBConnection) -> None:
    """A reader from a disabled pool must be closed rather than returned into a
    replacement pool, where it may have stale connection setup such as an old key."""
    with conn.read_ctx():
        old_reader = conn._borrowed_reader.reader
        conn.disable_read_pool()
        conn.enable_read_pool(size=POOL_SIZE)

    assert conn._readers_num == 0
    with pytest.raises(rsqlite.ProgrammingError):
        old_reader.cursor()
    with conn.read_ctx():
        assert conn._borrowed_reader.reader is not old_reader


@pytest.fixture(name='user_conn')
def fixture_user_conn(tmp_path: Path) -> Any:
    """A keyed sqlcipher user-type connection with the read pool enabled,
    mirroring how DBHandler sets up the user DB connection"""
    conn = DBConnection(
        path=str(tmp_path / 'user.db'),
        connection_type=DBConnectionType.USER,
        sql_vm_instructions_cb=100,
    )
    unlock_database(  # applies the key and switches to WAL mode
        db_connection=conn,
        password=USER_DB_PASSWORD,
        sqlcipher_version=4,
    )
    with conn.write_ctx() as cursor:
        cursor.execute('CREATE TABLE t(a INTEGER)')
        cursor.execute('INSERT INTO t VALUES (1)')
    conn.enable_read_pool(reader_setup=lambda reader: unlock_database(
        db_connection=reader,
        password=USER_DB_PASSWORD,
        sqlcipher_version=4,
        apply_optimizations=False,
    ))
    yield conn
    conn.close()


def test_user_db_keyed_pooled_reads(user_conn: DBConnection) -> None:
    """Pooled sqlcipher readers are keyed by reader_setup and read-only"""
    with user_conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM t').fetchone() == (1,)
        with pytest.raises(sqlcipher.OperationalError, match='readonly'):  # pylint: disable=no-member
            cursor.execute('INSERT INTO t VALUES (2)')

    with user_conn.write_ctx() as write_cursor:  # own-write fallback also works keyed
        write_cursor.execute('INSERT INTO t VALUES (2)')
        with user_conn.read_ctx() as cursor:
            assert cursor.execute('SELECT COUNT(*) FROM t').fetchone() == (2,)


def test_user_db_rekey_rebuilds_pool(user_conn: DBConnection) -> None:
    """The change_password flow: readers keyed with the old password are closed
    before the rekey and a fresh pool is keyed with the new one"""
    user_conn.disable_read_pool()
    with user_conn.write_ctx() as write_cursor:
        write_cursor.executescript("PRAGMA rekey='456';")
    user_conn.enable_read_pool(reader_setup=lambda reader: unlock_database(
        db_connection=reader,
        password='456',
        sqlcipher_version=4,
        apply_optimizations=False,
    ))
    with user_conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM t').fetchone() == (1,)


def test_user_db_failed_reader_setup_cleans_up(user_conn: DBConnection) -> None:
    """A reader_setup failure (e.g. wrong key) closes created readers, propagates
    and leaves the pool disabled so read_ctx falls back to the write connection"""
    user_conn.disable_read_pool()
    user_conn.enable_read_pool(reader_setup=lambda reader: unlock_database(
        db_connection=reader,
        password='wrong password',
        sqlcipher_version=4,
        apply_optimizations=False,
    ))
    with pytest.raises(sqlcipher.DatabaseError), user_conn.read_ctx():  # pylint: disable=no-member
        pass
    assert user_conn._read_pool is None
    with user_conn.read_ctx() as cursor:  # falls back to the write connection
        assert cursor.execute('SELECT COUNT(*) FROM t').fetchone() == (1,)


def test_user_db_integrity_check_on_pooled_reader(user_conn: DBConnection) -> None:
    """PRAGMA integrity_check is a pure read and must work on pooled readers,
    since db_integrity_check runs it through read_ctx"""
    with user_conn.read_ctx() as cursor:
        assert cursor.execute('PRAGMA integrity_check;').fetchall() == [('ok',)]


def test_concurrent_readers_and_writers_soak(conn: DBConnection) -> None:
    """Many readers and writers interleave without cursor resets or stale locks"""
    def writer(worker: int) -> None:
        for _ in range(20):
            with conn.write_ctx() as cursor:
                cursor.execute('INSERT INTO t(a) VALUES (?)', (worker,))
            time.sleep(0)

    def reader() -> None:
        for _ in range(20):
            with conn.read_ctx() as cursor:
                assert cursor.execute('SELECT COUNT(*) FROM t').fetchone()[0] >= 1
            time.sleep(0)

    tasks: list[Task] = []
    for worker in range(4):
        tasks.extend((spawn(writer, worker), spawn(reader)))
    wait(tasks)
    assert [task.exception for task in tasks] == [None] * len(tasks)
    with conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM t').fetchone() == (81,)
