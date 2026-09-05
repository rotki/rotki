import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import Location
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='UserDB v53->v54 upgrade')
def upgrade_v53_to_v54(db: DBHandler, progress_handler: DBUpgradeProgressHandler) -> None:
    """Upgrades the DB from v53 to v54. This happened in 1.45."""

    @progress_step(description='Add Sonic location.')
    def _add_sonic_location(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            'INSERT OR IGNORE INTO location(location, seq) VALUES (?, ?)',
            (Location.SONIC.serialize_for_db(), Location.SONIC.value),
        )

    @progress_step(description='Add Robinhood chain location.')
    def _add_robinhood_location(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            'INSERT OR IGNORE INTO location(location, seq) VALUES (?, ?)',
            (Location.ROBINHOOD.serialize_for_db(), Location.ROBINHOOD.value),
        )

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler)
