"""Tests for the cooperative cancellation machinery of phase 2 of the
gevent removal migration. See docs/designs/gevent_to_asyncio.md"""
import gevent
import pytest

from rotkehlchen.concurrency import (
    CancellationToken,
    TaskCancelledError,
    cancellable_sleep,
    checkpoint,
    current_token,
    exception_of,
    run_cancellable,
    spawn,
    wait,
)
from rotkehlchen.db.drivers.gevent import DBConnection, DBConnectionType


@pytest.fixture(name='transient_conn')
def fixture_transient_conn():
    conn = DBConnection(
        path=':memory:',
        connection_type=DBConnectionType.TRANSIENT,
        sql_vm_instructions_cb=100,
    )
    yield conn
    conn.close()


def test_cancellable_sleep_wakes_up_at_cancellation():
    token = CancellationToken()
    seen_token = []

    def task():
        seen_token.append(current_token() is token)
        while True:
            cancellable_sleep(10)

    greenlet = gevent.spawn(run_cancellable, token, task)
    gevent.sleep(0.05)  # let the task enter the sleep
    token.cancel('test cancel')
    greenlet.join(timeout=2)  # wakes up immediately, way before the 10 seconds pass
    assert greenlet.dead is True
    assert isinstance(greenlet.exception, TaskCancelledError)
    assert str(greenlet.exception) == 'test cancel'
    assert seen_token == [True]


def test_checkpoint_is_noop_outside_cancellable_tasks():
    assert current_token() is None
    checkpoint()  # does not raise
    cancellable_sleep(0)  # falls back to plain sleep, does not raise


def test_cancelled_before_start_never_runs():
    token = CancellationToken()
    token.cancel('cancelled before spawn')
    ran = []
    greenlet = gevent.spawn(run_cancellable, token, lambda: ran.append(1))
    greenlet.join(timeout=2)
    assert isinstance(greenlet.exception, TaskCancelledError)
    assert ran == []


def test_spawn_propagates_token_to_children():
    """Cancelling a task's token also cancels tasks it spawned through the seam"""
    token = CancellationToken()

    def child():
        while True:
            cancellable_sleep(10)

    def parent():
        child_task = spawn(child)
        wait([child_task])  # swallows the child's cancellation exception
        return child_task

    greenlet = gevent.spawn(run_cancellable, token, parent)
    gevent.sleep(0.05)  # let parent spawn the child and block on it
    token.cancel('cancel the whole tree')
    greenlet.join(timeout=2)
    assert greenlet.dead is True
    assert greenlet.exception is None  # parent hit no checkpoint after the wait
    assert isinstance(exception_of(greenlet.get()), TaskCancelledError)


def test_db_statement_aborts_at_cancellation(transient_conn):
    """A long running statement of a cancelled task is aborted by the progress
    callback checkpoint and surfaces as TaskCancelledError, leaving the
    connection usable."""
    token = CancellationToken()

    def long_query():
        with transient_conn.read_ctx() as cursor:
            cursor.execute(  # a recursive CTE that runs for a very long time
                'WITH RECURSIVE r(i) AS (VALUES(1) UNION ALL SELECT i+1 FROM r '
                'WHERE i < 10000000) SELECT MAX(i) FROM r',
            ).fetchone()

    greenlet = gevent.spawn(run_cancellable, token, long_query)
    gevent.sleep(0.1)  # give the query a chance to start
    token.cancel('abort the query')
    greenlet.join(timeout=10)
    assert greenlet.dead is True
    assert isinstance(greenlet.exception, TaskCancelledError)
    with transient_conn.read_ctx() as cursor:  # connection still works
        assert cursor.execute('SELECT 1').fetchone() == (1,)


def test_write_tx_rolls_back_at_cancellation(transient_conn):
    """TaskCancelledError does not inherit Exception, so make sure the write
    context rolls the transaction back for it too"""
    token = CancellationToken()

    def writer():
        with transient_conn.write_ctx() as cursor:
            cursor.execute('CREATE TABLE t(a INTEGER)')
            cursor.execute('INSERT INTO t VALUES (1)')
            token.cancel('cancelled mid-write')
            checkpoint()

    greenlet = gevent.spawn(run_cancellable, token, writer)
    greenlet.join(timeout=2)
    assert isinstance(greenlet.exception, TaskCancelledError)
    assert transient_conn._conn.in_transaction is False
    with transient_conn.read_ctx() as cursor:  # the whole transaction rolled back
        assert cursor.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='t'",
        ).fetchone() == (0,)


def test_savepoint_rolls_back_at_cancellation(transient_conn):
    """Savepoint contexts must roll back and release cleanly for a cancelled task"""
    with transient_conn.write_ctx() as cursor:
        cursor.execute('CREATE TABLE t(a INTEGER)')
        cursor.execute('INSERT INTO t VALUES (1)')

    token = CancellationToken()

    def task():
        with transient_conn.savepoint_ctx() as cursor:
            cursor.execute('INSERT INTO t VALUES (2)')
            token.cancel('cancelled mid-savepoint')
            checkpoint()

    greenlet = gevent.spawn(run_cancellable, token, task)
    greenlet.join(timeout=2)
    assert isinstance(greenlet.exception, TaskCancelledError)
    assert len(transient_conn.savepoints) == 0
    assert transient_conn.savepoint_greenlet_id is None
    with transient_conn.read_ctx() as cursor:  # only the committed row remains
        assert cursor.execute('SELECT a FROM t').fetchall() == [(1,)]


def test_cancelled_task_does_not_open_new_savepoints(transient_conn):
    token = CancellationToken()

    def task():
        token.cancel('cancelled before the savepoint')
        with transient_conn.savepoint_ctx():
            raise AssertionError('should never get here')

    greenlet = gevent.spawn(run_cancellable, token, task)
    greenlet.join(timeout=2)
    assert isinstance(greenlet.exception, TaskCancelledError)
    assert len(transient_conn.savepoints) == 0
