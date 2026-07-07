"""Tests for the pool of read-only connections that isolates read_ctx() readers
from write commits on the same DB (WAL mode). See DBConnection.enable_read_pool.
"""
import time
from pathlib import Path
from typing import Final

import pytest
import rsqlite

from rotkehlchen.concurrency import Task, spawn, wait
from rotkehlchen.db.drivers.sqlite import DBConnection, DBConnectionType

POOL_SIZE: Final = 2


@pytest.fixture(name='conn')
def fixture_conn(tmp_path: Path):
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


def test_write_through_read_cursor_raises(conn: DBConnection):
    """Pooled readers are opened with mode=ro so a write through read_ctx fails loudly"""
    with conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM t').fetchone() == (1,)
        with pytest.raises(rsqlite.OperationalError, match='readonly'):
            cursor.execute('INSERT INTO t(a) VALUES (2)')


def test_own_uncommitted_data_stays_visible(conn: DBConnection):
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


def test_readers_are_isolated_from_write_commits(conn: DBConnection):
    """The reason the pool exists: another thread's commit must neither reset an
    in-flight read statement nor leak uncommitted data into it"""
    with conn.write_ctx() as write_cursor:
        write_cursor.executemany('INSERT INTO t(a) VALUES (?)', [(i,) for i in range(2, 11)])

    read_results: list[int] = []

    def slow_reader() -> None:
        with conn.read_ctx() as cursor:
            cursor.execute('SELECT a FROM t')
            for _ in cursor:  # keep the statement active across the writer's commits
                read_results.append(1)
                time.sleep(0.01)

    def writer() -> None:
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


def test_uncommitted_data_invisible_to_other_threads(conn: DBConnection):
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


def test_nested_read_ctx_reuses_borrowed_reader(tmp_path: Path):
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


def test_enable_read_pool_is_noop_for_memory_db():
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


def test_close_with_borrowed_reader(conn: DBConnection):
    """Closing the connection while a reader is borrowed closes that reader when
    it is returned instead of leaking it"""
    with conn.read_ctx() as cursor:
        cursor.execute('SELECT COUNT(*) FROM t').fetchone()
        reader = conn._borrowed_reader.reader
        conn.close()
    # the read_ctx exit returned the reader to the closed pool, closing it
    with pytest.raises(rsqlite.ProgrammingError):
        reader.cursor()


def test_concurrent_readers_and_writers_soak(conn: DBConnection):
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
