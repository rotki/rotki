from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnectionPool


def globaldb_data_migration_2(conn: 'DBConnectionPool') -> None:
    """Introduced at 1.36.0
    - Removes number of queried yearn vaults to ensure that a refresh is made and
    users get the staking vaults.
    """
    with conn.write_ctx() as write_cursor:
        # Remove old setting if existing
        write_cursor.execute('DELETE FROM unique_cache WHERE key=?', ('YEARN_VAULTS',))
