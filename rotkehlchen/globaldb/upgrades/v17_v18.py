import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.sqlite import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='globaldb v17->v18 upgrade')
def migrate_to_v18(
        connection: DBConnection,
        progress_handler: DBUpgradeProgressHandler,
) -> None:
    """This upgrade takes place in v1.45.0."""

    @progress_step('Add the exchange futures asset type.')
    def _add_exchange_futures_asset_type(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            "INSERT OR IGNORE INTO asset_types(type, seq) VALUES (']', 29)",
        )

    perform_globaldb_upgrade_steps(connection, progress_handler)
