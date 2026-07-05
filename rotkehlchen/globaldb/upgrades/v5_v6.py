import logging
from typing import TYPE_CHECKING

from eth_utils.address import to_checksum_address

from rotkehlchen.db.utils import update_table_schema
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import CacheType
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.sqlite import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

V5_V6_UPGRADE_UNIQUE_CACHE_KEYS: set[CacheType] = {
    CacheType.CURVE_POOL_ADDRESS,
    CacheType.MAKERDAO_VAULT_ILK,
    CacheType.CURVE_GAUGE_ADDRESS,
    CacheType.YEARN_VAULTS,
}


@enter_exit_debug_log(name='GlobalDB v5->v6 upgrade')
def migrate_to_v6(connection: 'DBConnection', progress_handler: 'DBUpgradeProgressHandler') -> None:  # noqa: E501
    """This globalDB upgrade does the following:
    - Adds the `unique_cache` table.
    - Fixes the multiassets mappings ids to use checksummed addresses
    - Upgrades the multiasset_mappings to have unique collection_id+asset
    - Removes the VELO asset from the database

    This upgrade takes place in v1.31.0
    """
    @progress_step('Creating unique_cache table.')
    def _create_and_populate_unique_cache_table(cursor: 'DBCursor') -> None:
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
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' and name=?",
            ('general_cache',),
        )
        if cursor.fetchone() is None:  # If the general_cache table doesn't exist then there is nothing to transfer to the unique_cache table. We can exit immediately.  # noqa: E501
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

    @progress_step('Fixing unchecksummed assets in multiassets mappings.')
    def _fix_asset_in_multiasset_mappings(cursor: 'DBCursor') -> None:
        """
        Fix some assets that were not using checksummed addresses in the identifiers
        https://github.com/rotki/rotki/issues/6717
        """
        fixes = []
        cursor.execute('SELECT asset FROM multiasset_mappings')
        for (asset_id,) in cursor:
            if not asset_id.startswith('eip155'):
                continue
            try:
                address = asset_id.split(':')[-1]
                checksummed_address = to_checksum_address(address)
            except (IndexError, ValueError):
                log.error(f'Unexpected asset identifier {asset_id} found in the multiassets mapping')  # noqa: E501
                continue

            if checksummed_address == address:
                continue

            new_id = asset_id.replace(address, checksummed_address)
            fixes.append((new_id, asset_id))

        cursor.executemany('UPDATE multiasset_mappings SET asset=? WHERE asset=?', fixes)

    @progress_step('Updating multiasset mappings table schema.')
    def _update_multiasset_mappings(cursor: 'DBCursor') -> None:
        """Update the multiasset mapping table to have unique collection id + asset"""
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

    @progress_step('Tidying up VELO asset in the global DB.')
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
        cursor.execute('DELETE FROM assets WHERE identifier=?', ('VELO',))

    perform_globaldb_upgrade_steps(connection, progress_handler)
