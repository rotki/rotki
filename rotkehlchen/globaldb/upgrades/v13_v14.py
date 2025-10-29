import logging
from typing import TYPE_CHECKING

import rsqlite

from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='globaldb v13->v14 upgrade')
def migrate_to_v14(connection: 'DBConnection', progress_handler: 'DBUpgradeProgressHandler') -> None:  # noqa: E501
    """This globalDB upgrade does the following:
    - Swap SOL-2 to SOL throughout the global database.

    This upgrade takes place in v1.41.0"""

    @progress_step('Swap SOL-2 to SOL asset identifier in global database')
    def _swap_sol2_to_sol(write_cursor: 'DBCursor') -> None:
        """Swaps SOL-2 to SOL throughout the global database."""
        asset_columns = [
            ('assets', 'identifier'),
            ('counterparty_asset_mappings', 'local_id'),
            ('location_asset_mappings', 'local_id'),
        ]
        for table_name, column_name in asset_columns:
            write_cursor.execute(
                f'UPDATE {table_name} SET {column_name} = ? WHERE {column_name} = ?',
                ('SOL', 'SOL-2'),
            )

        # Update 38 might not have set correctly the collection for SOL due to being
        # executed before the id renaming. This logic is needed for those users that
        # pulled assets before using 1.41.0
        write_cursor.execute("INSERT OR REPLACE INTO asset_collections(id, name, symbol, main_asset) VALUES (512, 'Solana', 'SOL', 'SOL')")  # noqa: E501
        write_cursor.execute("INSERT OR IGNORE INTO multiasset_mappings(collection_id, asset) VALUES (512, 'SOL');")  # noqa: E501
        try:
            write_cursor.executescript("INSERT INTO assets(identifier, name, type) VALUES('solana/token:So11111111111111111111111111111111111111112', 'Wrapped SOL', 'Y'); INSERT INTO solana_tokens(identifier, token_kind, address, decimals, protocol) VALUES('solana/token:So11111111111111111111111111111111111111112', 'D', 'So11111111111111111111111111111111111111112', 9, NULL); INSERT INTO common_asset_details(identifier, symbol, coingecko, cryptocompare, forked, started, swapped_for) VALUES('solana/token:So11111111111111111111111111111111111111112', 'WSOL', 'solana', 'SOL', NULL, 1639612800, NULL);")  # noqa: E501
        except rsqlite.Error as e:
            log.warning(f'Not inserting WSOL in upgrade 14 due to {e}')

        try:
            write_cursor.execute("INSERT OR IGNORE INTO multiasset_mappings(collection_id, asset) VALUES (512, 'solana/token:So11111111111111111111111111111111111111112')")  # noqa: E501
        except rsqlite.Error as e:
            log.error(f'Failed to add WSOL to SOL collection due to {e}')

    @progress_step('Remove old Morpho cache key')
    def _remove_old_morpho_cache_key(write_cursor: 'DBCursor') -> None:
        """Remove the old Morpho cache key. The Morpho vault count is now stored by chain
        instead of one count for all chains.
        """
        write_cursor.execute('DELETE FROM unique_cache WHERE key=?', ('MORPHO_VAULTS',))

    perform_globaldb_upgrade_steps(connection, progress_handler)
