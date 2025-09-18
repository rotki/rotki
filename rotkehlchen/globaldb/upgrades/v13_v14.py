import logging
from typing import TYPE_CHECKING

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

    perform_globaldb_upgrade_steps(connection, progress_handler)
