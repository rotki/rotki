import logging
from typing import TYPE_CHECKING

from eth_utils.address import to_checksum_address

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
        insert_columns='collection_id, asset',
    )
    log.debug('Exit _upgrade_multiasset_mappings')


def _fix_asset_in_multiasset_mappings(cursor: 'DBCursor') -> None:
    """
    Fix some assets that were not using checksummed addresses in the identifiers
    https://github.com/rotki/rotki/issues/6717
    """
    log.debug('Enter _fix_asset_in_multiasset_mappings')
    fixes = []
    cursor.execute('SELECT asset FROM multiasset_mappings')
    for (asset_id,) in cursor:
        if not asset_id.startswith('eip155'):
            continue
        try:
            address = asset_id.split(':')[-1]
            checksummed_address = to_checksum_address(address)
        except (IndexError, ValueError):
            log.error(f'Unexpected asset identifier {asset_id} found in the multiassets mapping')
            continue

        if checksummed_address == address:
            continue

        new_id = asset_id.replace(address, checksummed_address)
        fixes.append((new_id, asset_id))

    cursor.executemany('UPDATE multiasset_mappings SET asset=? WHERE asset=?', fixes)
    log.debug('Exit _fix_asset_in_multiasset_mappings')


def _remove_velo_asset(cursor: 'DBCursor') -> None:
    """
    Remove the VELO asset from the global DB

    This is done as part of a consolidation process where we added VELO V1 and VELO V2 from
    Velodrome but our database also contained a VELO asset and a BNB version of it both not
    related to velodrome. As part of upgrade to V6 of the global DB we are replacing this VELO
    asset (not token) with its BNB version.

    The replacement took place in the upgrade to version 40 of the user db and in the global DB
    we only need to remove it.
    """
    log.debug('Enter _remove_velo_asset')
    cursor.execute('DELETE FROM assets WHERE identifier=?', ('VELO',))
    log.debug('Exit _remove_velo_asset')


def migrate_to_v6(connection: 'DBConnection') -> None:
    """This globalDB upgrade does the following:
    - Adds the `unique_cache` table.
    - Fixes the multiassets mappings ids to use checksummed addresses
    - Upgrades the multiasset_mappings to have unique collection_id+asset
    - Removes the VELO asset from the database

    This upgrade takes place in v1.31.0
    """
    log.debug('Entered globaldb v5->v6 upgrade')

    with connection.write_ctx() as cursor:
        _create_and_populate_unique_cache_table(cursor)
        _fix_asset_in_multiasset_mappings(cursor)
        _update_multiasset_mappings(cursor)
        _remove_velo_asset(cursor)
