import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='globaldb v16->v17 upgrade')
def migrate_to_v17(
        connection: 'DBConnection',
        progress_handler: 'DBUpgradeProgressHandler',
) -> None:
    """This upgrade takes place in v1.44.0."""

    @progress_step('Drop the unused location_unsupported_assets table.')
    def _drop_location_unsupported_assets_table(write_cursor: 'DBCursor') -> None:
        """The exchange unsupported-asset blocklist was removed, so the table that backed
        it is no longer used. Drop it."""
        write_cursor.execute('DROP TABLE IF EXISTS location_unsupported_assets')

    perform_globaldb_upgrade_steps(connection, progress_handler)
