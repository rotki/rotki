import json
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


@enter_exit_debug_log(name='UserDB v45->v46 upgrade')
def upgrade_v45_to_v46(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v45 to v46. This was in v1.37 release.

    - Remove balancer module from settings
    """
    @progress_step(description='Removing balancer module from user settings.')
    def _remove_balancer_module(write_cursor: 'DBCursor') -> None:
        if (active_modules_result := write_cursor.execute("SELECT value FROM settings where name='active_modules'").fetchone()) is None:  # noqa: E501
            return None

        try:
            active_modules = json.loads(active_modules_result[0])
        except json.JSONDecodeError:
            log.error(f'During v45->v46 DB upgrade a non-json active_modules entry was found: {active_modules_result[0]}.')  # noqa: E501
            return None

        write_cursor.execute(
            "UPDATE OR IGNORE settings SET value=? WHERE name='active_modules'",
            (json.dumps([module for module in active_modules if module != 'balancer']),),
        )

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
