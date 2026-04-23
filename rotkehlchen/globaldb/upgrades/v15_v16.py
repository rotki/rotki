import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='globaldb v15->v16 upgrade')
def migrate_to_v16(
        connection: 'DBConnection',
        progress_handler: 'DBUpgradeProgressHandler',
) -> None:
    """This upgrade takes place in v1.43.0."""

    @progress_step('Create price history timestamp order index.')
    def _create_price_history_timestamp_order_index(write_cursor: 'DBCursor') -> None:
        write_cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_price_history_timestamp_desc_order '
            'ON price_history (timestamp DESC, from_asset, to_asset, source_type);',
        )

    perform_globaldb_upgrade_steps(connection, progress_handler)
