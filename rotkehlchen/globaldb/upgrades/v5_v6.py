import logging
from typing import TYPE_CHECKING

from rotkehlchen.db.utils import update_table_schema
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


def _update_multiasset_mappings(cursor: 'DBCursor') -> None:
    """Update the multiasset mapping table to have unique collection id + asset"""
    log.debug('Enter _upgrade_multiasset_mappings')
    update_table_schema(
        write_cursor=cursor,
        table_name='multiasset_mappings',
        schema="""collection_id INTEGER NOT NULL,
        asset TEXT NOT NULL,
        FOREIGN KEY(collection_id) REFERENCES asset_collections(id) ON UPDATE CASCADE ON DELETE CASCADE,
        FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
        PRIMARY KEY(collection_id, asset)""",  # noqa: E501
        columns='collection_id, asset',
    )
    log.debug('Exit _upgrade_multiasset_mappings')


def migrate_to_v6(connection: 'DBConnection') -> None:
    """This globalDB upgrade does the following:
    - Adds the `unique_cache` table.
    - Upgrades the multiasset_mappings to have unique collection_id+asset

    This upgrade takes place in v1.31.0
    """
    log.debug('Entered globaldb v5->v6 upgrade')

    with connection.write_ctx() as cursor:
        _create_and_populate_unique_cache_table(cursor)
        _update_multiasset_mappings(cursor)
