import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

V5_V6_UPGRADE_UNIQUE_CACHE_KEYS: set[CacheType] = {
    CacheType.CURVE_POOL_ADDRESS,
    CacheType.MAKERDAO_VAULT_ILK,
    CacheType.CURVE_GAUGE_ADDRESS,
    CacheType.YEARN_VAULTS,
}


def _create_and_populate_unique_cache_table(cursor: 'DBCursor') -> None:
    log.debug('Enter _create_and_populate_unique_cache_table')

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS unique_cache (
            key TEXT NOT NULL PRIMARY KEY,
            value TEXT NOT NULL,
            last_queried_ts INTEGER NOT NULL
        );
        """,
    )

    cursor.execute(
        'SELECT COUNT(*) FROM sqlite_master WHERE type="table" and name=?',
        ('general_cache',),
    )
    if cursor.fetchone() is None:  # If the general_cache table doesn't exist then there is nothing to transfer to the unique_cache table. We can exit immediately.  # noqa: E501
        log.debug('Exit _create_and_populate_unique_cache_table')
        return

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
    log.debug('Exit _create_and_populate_unique_cache_table')


def migrate_to_v6(connection: 'DBConnection') -> None:
    """This globalDB upgrade does the following:
    - Adds the `unique_cache` table.
    """
    log.debug('Entered globaldb v5->v6 upgrade')

    with connection.write_ctx() as cursor:
        _create_and_populate_unique_cache_table(cursor)
