"""Tests for DBCursor semantics that the prefetch buffer must preserve"""
import pytest

from rotkehlchen.db.drivers.sqlite import DBConnection, DBConnectionType


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
