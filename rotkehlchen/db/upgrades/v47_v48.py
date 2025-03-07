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


@enter_exit_debug_log(name='UserDB v47->v48 upgrade')
def upgrade_v47_to_v48(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v47 to v48. This was in v1.39 release.

    - Add Hyperliquid as location
    """
    @progress_step(description='Adding new locations to the DB.')
    def _add_new_locations(write_cursor: 'DBCursor') -> None:
        write_cursor.execute(  # hyperliquid
            "INSERT OR IGNORE INTO location(location, seq) VALUES ('w', 55)",
        )

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
