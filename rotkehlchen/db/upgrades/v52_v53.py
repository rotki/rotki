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


@enter_exit_debug_log(name='UserDB v52->v53 upgrade')
def upgrade_v52_to_v53(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v52 to v53. This adds the Monad location."""

    @progress_step(description='Adding Monad location to the DB.')
    def _add_monad_location(write_cursor: 'DBCursor') -> None:
        write_cursor.executescript("""
        /* Monad */
        INSERT OR IGNORE INTO location(location, seq) VALUES ('y', 57);
        """)

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=False)
