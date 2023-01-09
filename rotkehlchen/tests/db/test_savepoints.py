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
        cursor2, savepoint2 = conn._enter_savepoint()  # also check manual savepoints
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
