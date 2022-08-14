from typing import TYPE_CHECKING

from rotkehlchen.constants.resolver import ETHEREUM_DIRECTIVE, strethaddress_to_identifier

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
        last_update_timestamp INTEGER NOT NULL,
        is_pinned INTEGER NOT NULL CHECK (is_pinned IN (0, 1))
    );
    """)


def _rename_assets_identifiers(cursor: 'DBCursor') -> None:
    """Version 1.26 includes the migration for the global db and the references to assets
    need to be updated also in this database"""
    cursor.execute('SELECT identifier FROM assets')
    old_id_to_new = {}
    for (identifier,) in cursor:
        if identifier.startswith(ETHEREUM_DIRECTIVE):
            old_id_to_new[identifier] = strethaddress_to_identifier(identifier[6:])

    sqlite_tuples = [(new_id, old_id) for old_id, new_id in old_id_to_new.items()]
    cursor.executemany('UPDATE assets SET identifier=? WHERE identifier=?', sqlite_tuples)


def upgrade_v34_to_v35(db: 'DBHandler') -> None:
    """Upgrades the DB from v34 to v35
    - Change tables where time is used as column name to timestamp
    - Add user_notes table
    """
    with db.user_write() as cursor:
        _rename_assets_identifiers(cursor)
        _refactor_time_columns(cursor)
        _create_new_tables(cursor)
