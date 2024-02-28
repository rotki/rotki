import logging
from pathlib import Path
from typing import TYPE_CHECKING
from rotkehlchen.errors.misc import DBUpgradeError


from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _create_and_populate_location_asset_mappings_table(cursor: 'DBCursor') -> None:
    """Adds and populates the `location_asset_mappings` table. These mappings are added using
    `rotkehlchen/data/populate_location_asset_mappings.sql`, which were all hardcoded till v1.32.1.
    """
    log.debug('Enter _create_and_populate_location_asset_mappings_table')
    cursor.execute("""CREATE TABLE IF NOT EXISTS location_asset_mappings (
        location TEXT,
        exchange_symbol TEXT NOT NULL,
        local_id TEXT NOT NULL COLLATE NOCASE,
        UNIQUE (location, exchange_symbol)
    );""")
    # check if the SQL file exists
    if (
        sql_file := Path(__file__).resolve().parent.parent.parent / 'data' / 'populate_location_asset_mappings.sql'  # noqa: E501
    ).exists():  # populate the mappings for all the exchanges
        cursor.execute(sql_file.read_text(encoding='utf8'))
    else:
        raise DBUpgradeError('Could not find populate_location_asset_mappings.sql for v6->v7 upgrade in globalDB')  # noqa: E501
    log.debug('Exit _create_and_populate_location_asset_mappings_table')


def migrate_to_v7(connection: 'DBConnection') -> None:
    """This globalDB upgrade does the following:
    - Adds and populates the `location_asset_mappings` table.

    This upgrade takes place in v1.33.0"""
    log.debug('Entered globaldb v6->v7 upgrade')

    with connection.write_ctx() as cursor:
        _create_and_populate_location_asset_mappings_table(cursor)

    log.debug('Finished globaldb v6->v7 upgrade')
