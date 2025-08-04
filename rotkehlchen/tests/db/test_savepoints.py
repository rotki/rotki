from contextlib import suppress

import gevent
import pytest
import rsqlite

from rotkehlchen.db.drivers.gevent import ContextError, DBConnection, DBConnectionType
from rotkehlchen.errors.asset import UnknownAsset


def test_unnamed_savepoints():
    conn = DBConnection(
        path=':memory:',
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=0,
    )
    conn.execute('CREATE TABLE a(b INTEGER PRIMARY KEY)')
    with conn.savepoint_ctx() as cursor1:
        assert len(conn.savepoints) == 1
        savepoint1 = next(iter(conn.savepoints))
        cursor1.execute('INSERT INTO a VALUES (1)')
        cursor2, savepoint2 = conn._enter_savepoint()  # also check manual savepoints
        assert list(conn.savepoints) == [savepoint1, savepoint2]
        cursor2.execute('INSERT INTO a VALUES (2)')
        # make sure that 2 was added
        assert cursor1.execute('SELECT b FROM a').fetchall() == [(1,), (2,)]
        conn.rollback_savepoint()
        # check that the second savepoint was NOT released since it was only rolled back
        assert list(conn.savepoints) == [savepoint1, savepoint2]
        assert cursor1.execute('SELECT b FROM a').fetchall() == [(1,)]  # 2 should not be there
        cursor1.execute('INSERT INTO a VALUES (3)')  # add one more value after the rollback
    assert len(conn.savepoints) == 0  # check that we released successfully
    # And make sure that the data is saved
    assert conn.execute('SELECT b FROM a').fetchall() == [(1,), (3,)]


def test_savepoint_errors():
    conn = DBConnection(
        path=':memory:',
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=0,
    )
    with pytest.raises(ContextError):
        conn.release_savepoint()

    conn._enter_savepoint('point')
    with pytest.raises(ContextError), conn._enter_savepoint('point'):
        ...

    with pytest.raises(ContextError):
        conn.rollback_savepoint('abc')


def test_write_transaction_with_savepoint():
    """Test that opening a savepoint within a write transaction in the
    same greenlet is okay"""
    conn = DBConnection(
        path=':memory:',
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=0,
    )
    conn.execute('CREATE TABLE a(b INTEGER PRIMARY KEY)')
    with conn.write_ctx() as write_cursor:
        write_cursor.execute('INSERT INTO a VALUES (1)')
        with conn.savepoint_ctx() as savepoint_cursor:
            savepoint_cursor.execute('INSERT INTO a VALUES (2)')

    with conn.read_ctx() as cursor:
        assert cursor.execute('SELECT b from a').fetchall() == [(1,), (2,)]


def test_write_transaction_with_savepoint_other_context():
    """Test that opening a savepoint from a different greenlet while a write
    transaction is already open from another greenlet waits for the original to finish"""
    def other_context(conn: 'DBConnection', first_run: bool) -> None:
        with conn.savepoint_ctx() as savepoint1_cursor:
            values = (2,) if first_run else (4,)
            savepoint1_cursor.execute('INSERT INTO a VALUES (?)', values)
            if first_run:
                return
            with suppress(ValueError), conn.savepoint_ctx() as savepoint2_cursor:
                savepoint2_cursor.execute('INSERT INTO a VALUES (5)')
                raise ValueError('Test rollback')

    conn = DBConnection(
        path=':memory:',
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=0,
    )
    conn.execute('CREATE TABLE a(b INTEGER PRIMARY KEY)')
    with conn.write_ctx() as write_cursor:
        write_cursor.execute('INSERT INTO a VALUES (1)')
        greenlet1 = gevent.spawn(other_context, conn, True)
        gevent.sleep(.3)  # context switch for a bit to let the other greenlet run
        assert greenlet1.exception is None
        assert greenlet1.dead is False, 'the other greenlet should still run'

    with conn.read_ctx() as cursor:
        assert cursor.execute('SELECT b from a').fetchall() == [(1,)], 'other greenlet should not have written to the DB'  # noqa: E501

    gevent.joinall([greenlet1])  # wait till the other greenlet finishes
    with conn.read_ctx() as cursor:  # make sure it wrote in the DB
        assert cursor.execute('SELECT b from a').fetchall() == [(1,), (2,)], 'other greenlet should write to the DB'  # noqa: E501

    # now let's try with the other greenlet also rolling back part of the savepoint
    with conn.write_ctx() as write_cursor:
        write_cursor.execute('INSERT INTO a VALUES (3)')
        greenlet1 = gevent.spawn(other_context, conn, False)
        gevent.sleep(.3)  # context switch for a bit to let the other greenlet run
        assert greenlet1.exception is None
        assert greenlet1.dead is False, 'the other greenlet should still run'

    with conn.read_ctx() as cursor:
        assert cursor.execute('SELECT b from a').fetchall() == [(1,), (2,), (3,)], 'other greenlet should not have written to the DB'  # noqa: E501

    gevent.joinall([greenlet1])  # wait till the other greenlet finishes
    with conn.read_ctx() as cursor:  # make sure it wrote in the DB but not the last one
        assert cursor.execute('SELECT b from a').fetchall() == [(1,), (2,), (3,), (4,)], 'other greenlet should write to the DB'  # noqa: E501


def test_savepoint_with_write_transaction():
    """Test that a write transaction under a savepoint can still happen by
    switching to a savepoint instead"""
    conn = DBConnection(
        path=':memory:',
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=0,
    )
    conn.execute('CREATE TABLE a(b INTEGER PRIMARY KEY)')
    with conn.savepoint_ctx() as savepoint_cursor:
        savepoint_cursor.execute('INSERT INTO a VALUES (1)')
        with conn.write_ctx() as write_cursor:
            write_cursor.execute('INSERT INTO a VALUES (2)')

    with conn.read_ctx() as cursor:
        assert cursor.execute('SELECT b from a').fetchall() == [(1,), (2,)]

    with suppress(ValueError), conn.savepoint_ctx() as savepoint_cursor:
        savepoint_cursor.execute('INSERT INTO a VALUES (3)')
        with conn.write_ctx() as write_cursor:
            write_cursor.execute('INSERT INTO a VALUES (4)')
            raise ValueError('Test rollback')

    with conn.read_ctx() as cursor:
        assert cursor.execute('SELECT b from a').fetchall() == [(1,), (2,)]


def test_savepoint_with_write_transaction_other_context():
    """Test that a write transaction after a savepoint but in a different greenlet
    does not continue the savepoint but instead waits"""
    def other_context(conn) -> None:
        with conn.write_ctx() as write_cursor:
            write_cursor.execute('INSERT INTO a VALUES (4)')

    conn = DBConnection(
        path=':memory:',
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=0,
    )
    conn.execute('CREATE TABLE a(b INTEGER PRIMARY KEY)')
    with conn.savepoint_ctx() as savepoint_cursor:
        savepoint_cursor.execute('INSERT INTO a VALUES (1)')
        greenlet1 = gevent.spawn(other_context, conn)
        gevent.sleep(.3)  # context switch for a bit to let the other greenlet run
        assert greenlet1.exception is None
        assert greenlet1.dead is False, 'the other greenlet should still run'

    with conn.read_ctx() as cursor:
        assert cursor.execute('SELECT b from a').fetchall() == [(1,)], 'other greenlet should not have written to the DB'  # noqa: E501

    gevent.joinall([greenlet1])  # wait till the other greenlet finishes
    with conn.read_ctx() as cursor:  # make sure it wrote in the DB
        assert cursor.execute('SELECT b from a').fetchall() == [(1,), (4,)], 'other greenlet should write to the DB'  # noqa: E501


def test_open_savepoint_with_savepoint_other_context():
    """Test that opening a savepoint while a savepoint queue is already open in
    another greenlet waits until the first one is completely done"""
    def other_context(conn, first_run) -> None:
        with conn.savepoint_ctx() as savepoint1_cursor:
            values = (2,) if first_run else (4,)
            savepoint1_cursor.execute('INSERT INTO a VALUES (?)', values)
            if first_run:
                return
            with suppress(ValueError), conn.savepoint_ctx() as savepoint2_cursor:
                savepoint2_cursor.execute('INSERT INTO a VALUES (5)')
                raise ValueError('Test rollback')

    conn = DBConnection(
        path=':memory:',
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=0,
    )
    conn.execute('CREATE TABLE a(b INTEGER PRIMARY KEY)')
    with conn.savepoint_ctx() as savepoint_cursor:
        savepoint_cursor.execute('INSERT INTO a VALUES (1)')
        greenlet1 = gevent.spawn(other_context, conn, True)
        gevent.sleep(.3)  # context switch for a bit to let the other greenlet run
        assert greenlet1.exception is None
        assert greenlet1.dead is False, 'the other greenlet should still run'

    with conn.read_ctx() as cursor:
        assert cursor.execute('SELECT b from a').fetchall() == [(1,)], 'other greenlet should not have written to the DB'  # noqa: E501

    gevent.joinall([greenlet1])  # wait till the other greenlet finishes
    with conn.read_ctx() as cursor:  # make sure it wrote in the DB
        assert cursor.execute('SELECT b from a').fetchall() == [(1,), (2,)], 'other greenlet should write to the DB'  # noqa: E501

    # now let's try with the other greenlet also rolling back part of the savepoint
    with conn.savepoint_ctx() as savepoint_cursor:
        savepoint_cursor.execute('INSERT INTO a VALUES (3)')
        greenlet1 = gevent.spawn(other_context, conn, False)
        gevent.sleep(.3)  # context switch for a bit to let the other greenlet run
        assert greenlet1.exception is None
        assert greenlet1.dead is False, 'the other greenlet should still run'

    with conn.read_ctx() as cursor:
        assert cursor.execute('SELECT b from a').fetchall() == [(1,), (2,), (3,)], 'other greenlet should not have written to the DB'  # noqa: E501

    gevent.joinall([greenlet1])  # wait till the other greenlet finishes
    with conn.read_ctx() as cursor:  # make sure it wrote in the DB but not the last one
        assert cursor.execute('SELECT b from a').fetchall() == [(1,), (2,), (3,), (4,)], 'other greenlet should write to the DB'  # noqa: E501


def test_rollback_in_savepoints():
    """
    Test that savepoints are released when an error is raised. This verifies
    that a rollback is always followed up by a release since that is required.
    """
    conn = DBConnection(
        path=':memory:',
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=0,
    )

    with (
        suppress(UnknownAsset),
        conn.savepoint_ctx(savepoint_name='mysave') as savepoint_cursor,
    ):
        savepoint_cursor.execute('CREATE TABLE mytable(age INTEGER PRIMARY KEY)')
        # raise the error to trigger the except clause in savepoint_ctx
        raise UnknownAsset('ETH')

    # leaving the with statement should have released the savepoint and trying to release
    # again the savepoint should raise an error because we have already released it.
    with pytest.raises(rsqlite.OperationalError):
        conn.execute("RELEASE SAVEPOINT 'mysave'")
