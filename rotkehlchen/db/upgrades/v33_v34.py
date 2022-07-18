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


def upgrade_v33_to_v34(db: 'DBHandler') -> None:
    """Upgrades the DB from v33 to v34
    - Change tables where time is used as column name to timestamp
    """
    with db.user_write() as cursor:
        _refactor_time_columns(cursor)
