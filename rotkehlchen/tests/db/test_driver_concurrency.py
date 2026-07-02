"""Stress test for the dual-mode DB driver: many concurrent tasks mixing write
transactions, savepoint stacks (with rollbacks) and readers on one connection.

Exercises the transaction-slot locking that replaced the poll-a-field wait loops
in phase 3 of the gevent removal migration (docs/designs/gevent_to_asyncio.md).
The tests run under gevent (as the whole suite does until the flip), but the
THREADING parametrization exercises the exact code paths that stay after it.
"""
import time

import gevent
import pytest

from rotkehlchen.db.drivers.gevent import DBConnection, DBConnectionType, SchedulingMode

WORKERS = 5
ITERATIONS = 20


@pytest.fixture(
    name='conn',
    params=[SchedulingMode.GEVENT, SchedulingMode.THREADING],
    ids=['gevent', 'threading'],
)
def fixture_conn(request):
    conn = DBConnection(
        path=':memory:',
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=100,
        scheduling_mode=request.param,
    )
    with conn.write_ctx() as cursor:
        cursor.execute('CREATE TABLE t(id INTEGER PRIMARY KEY AUTOINCREMENT, worker INTEGER)')
    yield conn
    conn.close()


def test_concurrent_writers_savepoints_and_readers(conn: DBConnection):
    """Soak the transaction slot: writers, savepoint stacks with partial rollbacks
    and readers all interleave and the connection state stays consistent"""
    def writer(worker: int) -> None:
        for _ in range(ITERATIONS):
            with conn.write_ctx() as cursor:
                cursor.execute('INSERT INTO t(worker) VALUES (?)', (worker,))
            time.sleep(0)  # yield so tasks interleave

    def savepointer(worker: int) -> None:
        for i in range(ITERATIONS):
            try:
                with conn.savepoint_ctx() as cursor:
                    cursor.execute('INSERT INTO t(worker) VALUES (?)', (worker,))
                    with conn.savepoint_ctx() as nested_cursor:  # nested savepoint
                        nested_cursor.execute('INSERT INTO t(worker) VALUES (?)', (worker,))
                        if i % 3 == 0:  # roll back BOTH inserts every third iteration
                            raise ValueError('rollback the whole stack')
            except ValueError:
                pass
            time.sleep(0)

    def mixer(worker: int) -> None:
        """A savepoint with a write_ctx nested inside it, like upgrade/import code does"""
        for _ in range(ITERATIONS):
            with conn.savepoint_ctx() as cursor:
                cursor.execute('INSERT INTO t(worker) VALUES (?)', (worker,))
                with conn.write_ctx() as write_cursor:  # becomes a savepoint internally
                    write_cursor.execute('INSERT INTO t(worker) VALUES (?)', (worker,))
            time.sleep(0)

    def reader() -> None:
        for _ in range(ITERATIONS):
            with conn.read_ctx() as cursor:
                count = cursor.execute('SELECT COUNT(*) FROM t').fetchone()[0]
                assert count >= 0
            time.sleep(0)

    tasks: list[gevent.Greenlet] = []
    for worker in range(WORKERS):
        tasks.extend((
            gevent.spawn(writer, worker),
            gevent.spawn(savepointer, WORKERS + worker),
            gevent.spawn(mixer, 2 * WORKERS + worker),
            gevent.spawn(reader),
        ))
    gevent.joinall(tasks)
    assert [task.exception for task in tasks] == [None] * len(tasks)

    # every worker's committed rows must all be there:
    # writers commit ITERATIONS rows; savepointers commit 2 rows per iteration
    # except every third which rolls back both; mixers commit 2 rows per iteration
    rolled_back = len(range(0, ITERATIONS, 3))
    expected_savepointer_rows = 2 * (ITERATIONS - rolled_back)
    with conn.read_ctx() as cursor:
        rows = dict(cursor.execute('SELECT worker, COUNT(*) FROM t GROUP BY worker'))
    for worker in range(WORKERS):
        assert rows[worker] == ITERATIONS
        assert rows[WORKERS + worker] == expected_savepointer_rows
        assert rows[2 * WORKERS + worker] == 2 * ITERATIONS

    # and the connection's transaction slot must be fully released
    assert len(conn.savepoints) == 0
    assert conn.savepoint_task_ident is None
    assert conn.write_task_ident is None
    assert conn.transaction_lock.locked() is False
    assert conn._conn.in_transaction is False
