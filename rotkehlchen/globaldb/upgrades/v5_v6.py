import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import GeneralCacheType


if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

V5_V6_UPGRADE_UNIQUE_CACHE_KEYS: set[GeneralCacheType] = {
    GeneralCacheType.CURVE_POOL_ADDRESS,
    GeneralCacheType.MAKERDAO_VAULT_ILK,
    GeneralCacheType.CURVE_GAUGE_ADDRESS,
    GeneralCacheType.YEARN_VAULTS,
}


def _create_new_tables(cursor: 'DBCursor') -> None:
    log.debug('Enter _create_new_tables')
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS unique_cache (
            key TEXT NOT NULL PRIMARY KEY,
            value TEXT NOT NULL,
            last_queried_ts INTEGER NOT NULL
        );
        """,
    )
    log.debug('Exit _create_new_tables')


def _transfer_unique_cache_data(cursor: 'DBCursor') -> None:
    log.debug('Enter _transfer_unique_cache_data')
    for key_part in V5_V6_UPGRADE_UNIQUE_CACHE_KEYS:
        cursor.execute(
            'INSERT OR IGNORE INTO unique_cache '
            'SELECT * FROM general_cache WHERE key LIKE ?',
            (f'{key_part.serialize()}%',),
        )
        cursor.execute(
            'DELETE FROM general_cache WHERE key LIKE ?',
            (f'{key_part.serialize()}%',),
        )
    log.debug('Exit _transfer_unique_cache_data')


def migrate_to_v6(connection: 'DBConnection') -> None:
    """This globalDB upgrade does the following:
    - Adds the `unique_cache` table.
    """
    log.debug('Entered globaldb v5->v6 upgrade')

    with connection.write_ctx() as cursor:
        _create_new_tables(cursor)
        _transfer_unique_cache_data(cursor)
