import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='UserDB v51->v52 upgrade')
def upgrade_v51_to_v52(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v51 to v52. This adds Bit2me exchange support."""

    @progress_step(description='Adding Bit2me location to the DB.')
    def _add_bit2me_location(write_cursor: 'DBCursor') -> None:
        write_cursor.executescript("""
        /* Bit2me */
        INSERT OR IGNORE INTO location(location, seq) VALUES ('y', 57);
        """)

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
