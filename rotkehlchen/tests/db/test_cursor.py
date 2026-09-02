"""Tests for DBCursor semantics that the prefetch buffer must preserve"""
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import pytest
import rsqlite

from rotkehlchen.db.drivers.sqlite import DBConnection, DBConnectionType

if TYPE_CHECKING:
    from pathlib import Path


def _execute_query(connection: DBConnection) -> None:
    with connection.read_ctx() as cursor:
        cursor.execute('SELECT 1').fetchone()


@pytest.fixture(name='conn')
def fixture_conn():
    conn = DBConnection(
        path=':memory:',
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=100,
    )
    with conn.write_ctx() as cursor:
        cursor.execute('CREATE TABLE t(a INTEGER)')
        cursor.executemany('INSERT INTO t(a) VALUES (?)', [(i,) for i in range(5)])
    yield conn
    conn.close()


@pytest.mark.parametrize('size', [0, -2])
def test_fetchmany_nonpositive_size_returns_remaining(conn: DBConnection, size: int):
    """The underlying drivers treat a non-positive fetchmany size as no limit
    and return all remaining rows -- the prefetch buffer must mirror that
    instead of returning nothing"""
    with conn.read_ctx() as cursor:
        cursor.execute('SELECT a FROM t ORDER BY a')
        assert next(cursor) == (0,)  # fills the prefetch buffer with the remaining rows
        assert cursor.fetchmany(size) == [(1,), (2,), (3,), (4,)]

    with conn.read_ctx() as cursor:  # also without any prefetched rows buffered
        cursor.execute('SELECT a FROM t ORDER BY a')
        assert cursor.fetchmany(size) == [(0,), (1,), (2,), (3,), (4,)]


def test_fetchmany_mixes_prefetched_and_remaining_rows(
        conn: DBConnection,
        monkeypatch: pytest.MonkeyPatch,
):
    """A fetchmany larger than the prefetch buffer serves the buffered rows
    first and completes from the underlying cursor"""
    monkeypatch.setattr('rotkehlchen.db.drivers.sqlite.CURSOR_PREFETCH_ROWS', 2)
    with conn.read_ctx() as cursor:
        cursor.execute('SELECT a FROM t ORDER BY a')
        assert next(cursor) == (0,)  # prefetches rows 0 and 1, leaving 1 buffered
        assert cursor.fetchmany(4) == [(1,), (2,), (3,), (4,)]


def test_connection_close_closes_retained_cursor(conn: DBConnection) -> None:
    cursor = conn.cursor()
    cursor.execute('SELECT 1')

    conn.close()

    with pytest.raises(rsqlite.ProgrammingError, match='closed cursor'):
        cursor.fetchone()


def test_cross_thread_statement_does_not_retain_database(tmp_path: Path) -> None:
    database_path = tmp_path / 'cross-thread.db'
    connection = DBConnection(
        path=database_path,
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=100,
        cached_statements=0,
    )
    with ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(_execute_query, connection).result()

    connection.close()

    database_path.unlink()
