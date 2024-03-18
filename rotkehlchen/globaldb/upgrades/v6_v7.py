from pathlib import Path
from typing import TYPE_CHECKING

from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.logging import enter_exit_debug_log

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor


def upgrade_from_sql(cursor: 'DBCursor', filename: str) -> None:
    """Executes SQL from the given file in the globalDB upgrade"""
    if (  # check if the SQL file exists
        sql_file := Path(__file__).resolve().parent.parent.parent / 'data' / f'{filename}.sql'
    ).exists():  # populate the mappings for all the exchanges
        cursor.execute(sql_file.read_text(encoding='utf8'))
    else:
        raise DBUpgradeError(f'Could not find {filename}.sql for v6->v7 upgrade in globalDB')


@enter_exit_debug_log()
def _create_and_populate_location_asset_mappings_table(cursor: 'DBCursor') -> None:
    """Adds and populates the `location_asset_mappings` table. These mappings are added using
    `rotkehlchen/data/populate_location_asset_mappings.sql`, which were all hardcoded till v1.32.XX.
    """  # noqa: E501
    cursor.execute("""CREATE TABLE IF NOT EXISTS location_asset_mappings (
        location TEXT,
        exchange_symbol TEXT NOT NULL,
        local_id TEXT NOT NULL COLLATE NOCASE,
        UNIQUE (location, exchange_symbol)
    );""")
    upgrade_from_sql(cursor=cursor, filename='populate_location_asset_mappings')


@enter_exit_debug_log()
def _create_and_populate_location_unsupported_assets_table(cursor: 'DBCursor') -> None:
    """Adds and populates the `location_unsupported_assets` table. These assets are added using
    `rotkehlchen/data/populate_location_unsupported_assets.sql`, which were all hardcoded till v1.32.XX.
    """  # noqa: E501
    cursor.execute("""CREATE TABLE IF NOT EXISTS location_unsupported_assets (
        location CHAR(1) NOT NULL,
        exchange_symbol TEXT NOT NULL,
        UNIQUE (location, exchange_symbol)
    );""")
    upgrade_from_sql(cursor=cursor, filename='populate_location_unsupported_assets')


@enter_exit_debug_log(name='globaldb v6->v7 upgrade')
def migrate_to_v7(connection: 'DBConnection') -> None:
    """This globalDB upgrade does the following:
    - Adds and populates the `location_asset_mappings` table.
    - Adds and populates the `location_unsupported_assets` table.

    This upgrade takes place in v1.33.0"""
    with connection.write_ctx() as cursor:
        _create_and_populate_location_asset_mappings_table(cursor)
        _create_and_populate_location_unsupported_assets_table(cursor)
