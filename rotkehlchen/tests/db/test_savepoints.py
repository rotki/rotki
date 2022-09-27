import sqlite3

import pytest

from rotkehlchen.db.drivers.gevent import ContextError, DBConnection, DBConnectionType


def test_unnamed_savepoints():
    conn = DBConnection(
        path=':memory:',
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=0,
    )
    conn.execute('CREATE TABLE a(b INTEGER PRIMARY KEY)')
    with conn.savepoint_ctx() as cursor1:
        assert len(conn.savepoints) == 1
        savepoint1 = list(conn.savepoints)[0]
        cursor1.execute('INSERT INTO a VALUES (1)')
        cursor2, savepoint2 = conn.enter_savepoint()  # also check manual savepoints
        assert list(conn.savepoints) == [savepoint1, savepoint2]
        cursor2.execute('INSERT INTO a VALUES (2)')
        # make sure that 2 was added
        assert cursor1.execute('SELECT b FROM a').fetchall() == [(1,), (2,)]
        conn.rollback_savepoint()
        # check that the second savepoint was rolled back
        assert list(conn.savepoints) == [savepoint1]
        assert cursor1.execute('SELECT b FROM a').fetchall() == [(1,)]  # 2 should not be there
        cursor1.execute('INSERT INTO a VALUES (3)')  # add one more value after the rollback
    assert len(conn.savepoints) == 0  # check that we released successfully
    # And make sure that the data is saved
    assert conn.execute('SELECT b FROM a').fetchall() == [(1,), (3,)]


def test_named_savepoints():
    conn = DBConnection(
        path=':memory:',
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=0,
    )
    conn.execute('CREATE TABLE a(b INTEGER PRIMARY KEY)')
    savepoint1 = 'savepointXYZ'
    with pytest.raises(sqlite3.Error):
        with conn.savepoint_ctx(savepoint1) as cursor1:
            assert list(conn.savepoints) == [savepoint1]
            cursor1.execute('INSERT INTO a VALUES (1)')
            _, savepoint2 = conn.enter_savepoint('point2')
            cursor3, savepoint3 = conn.enter_savepoint()  # enter a couple more savepoints
            assert list(conn.savepoints) == [savepoint1, savepoint2, savepoint3]
            cursor3.execute('INSERT INTO a VALUES (2)')
            # check that values are there
            assert cursor3.execute('SELECT b FROM a').fetchall() == [(1,), (2,)]
            # And now don't rollback manually entered savepoints,
            # but rollback directly to the first one
            cursor3.execute('INSERT INTO a VALUES (1)')  # make an error
    # And check that everything was rolled back
    assert len(conn.savepoints) == 0
    assert conn.execute('SELECT b FROM a').fetchall() == []


def test_savepoint_errors():
    conn = DBConnection(
        path=':memory:',
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=0,
    )
    with pytest.raises(ContextError):
        conn.release_savepoint()

    conn.enter_savepoint('point')
    with pytest.raises(ContextError):
        with conn.enter_savepoint('point'):
            ...

    with pytest.raises(ContextError):
        conn.rollback_savepoint('abc')
