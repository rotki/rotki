import gevent
import pytest


@pytest.mark.parametrize('sql_vm_instructions_cb', [1])
def test_wal_checkpoint_lock(database):
    """Test that verifies the fix for issue #5038.

    It reproduces the actual scenario where multiple concurrent readers during a WAL checkpoint
    can lead to a database locked error
    """
    errors, attempts, max_attempts = [], 0, 50

    def db_reader():
        """Simulate continuous global DB operations that trigger progress callbacks"""
        while attempts < max_attempts and len(errors) == 0:
            # These operations will trigger progress callbacks frequently
            with database.conn.read_ctx() as cursor:
                cursor.execute('SELECT identifier FROM assets LIMIT 50')
                cursor.fetchall()

            with database.conn.read_ctx() as cursor:
                cursor.execute('SELECT COUNT(*) FROM assets')
                cursor.fetchone()

            gevent.sleep(0)

    def checkpoint_worker():
        """Perform WAL checkpoint operations that should trigger the bug without the fix"""
        nonlocal attempts, errors

        while attempts < max_attempts and len(errors) == 0:
            attempts += 1

            try:
                # Add some data to ensure WAL has content to checkpoint
                with database.user_write() as write_cursor:
                    write_cursor.execute(
                        'INSERT OR REPLACE INTO settings(name, value) VALUES (?, ?)',
                        (f'test_checkpoint_{attempts}', f'value_{attempts}'),
                    )

                # This is the critical operation that fails without the lock
                # The new wal_checkpoint() method should prevent the lock error
                database.conn.wal_checkpoint()

            except Exception as e:
                if 'locked' in str(e).lower():
                    errors.append(e)

    greenlets = [
        gevent.spawn(db_reader),
        gevent.spawn(db_reader),  # Multiple readers for more callbacks
        gevent.spawn(checkpoint_worker),
    ]
    gevent.joinall(greenlets, timeout=30)

    # With the fix (using wal_checkpoint method with in_callback lock),
    # there should be no 'database table is locked' errors
    assert len(errors) == 0, f'WAL checkpoint failed with lock errors: {errors}'
