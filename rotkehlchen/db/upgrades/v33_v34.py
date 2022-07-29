from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor


def _refactor_time_columns(cursor: 'DBCursor') -> None:
    """
    The tables that contained time instead of timestamp as column names and need
    to be changed were:
    - timed_balances
    - timed_location_data
    - ethereum_accounts_details
    - trades
    - asset_movements
    """
    cursor.execute('ALTER TABLE timed_balances RENAME COLUMN time TO timestamp')
    cursor.execute('ALTER TABLE timed_location_data RENAME COLUMN time TO timestamp')
    cursor.execute('ALTER TABLE ethereum_accounts_details RENAME COLUMN time TO timestamp')
    cursor.execute('ALTER TABLE trades RENAME COLUMN time TO timestamp')
    cursor.execute('ALTER TABLE asset_movements RENAME COLUMN time TO timestamp')


def _create_new_tables(cursor: 'DBCursor') -> None:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_notes(
        identifier INTEGER NOT NULL PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        location TEXT NOT NULL,
        last_update_timestamp INTEGER NOT NULL
    );
    """)


def upgrade_v33_to_v34(db: 'DBHandler') -> None:
    """Upgrades the DB from v33 to v34
    - Change tables where time is used as column name to timestamp
    - Add user_notes table
    """
    with db.user_write() as cursor:
        _refactor_time_columns(cursor)
        _create_new_tables(cursor)
