from typing import TYPE_CHECKING

from rotkehlchen.logging import enter_exit_debug_log
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.sqlite import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


@enter_exit_debug_log(name='globaldb v18->v19 upgrade')
def migrate_to_v19(
        connection: DBConnection,
        progress_handler: DBUpgradeProgressHandler,
) -> None:
    """Add Birdeye as a historical price source.

    This upgrade takes place in v1.45
    """

    @progress_step('Adding Birdeye to price_history_source_types')
    def _add_birdeye_price_source(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            'INSERT OR IGNORE INTO price_history_source_types(type, seq) VALUES (?, ?)',
            ('L', 12),
        )

    perform_globaldb_upgrade_steps(
        connection=connection,
        progress_handler=progress_handler,
        should_vacuum=False,
    )
