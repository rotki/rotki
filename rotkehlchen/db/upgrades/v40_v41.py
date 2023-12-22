import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _add_cache_table(write_cursor: 'DBCursor') -> None:
    """Add a new key-value cache table for this upgrade"""
    log.debug('Enter _add_cache_table')
    write_cursor.execute("""CREATE TABLE IF NOT EXISTS key_value_cache (
        name TEXT NOT NULL PRIMARY KEY,
        value TEXT
    );""")
    log.debug('Exit _add_cache_table')


def upgrade_v40_to_v41(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v40 to v41. This was in v1.32 release.

        - Create a new table for key-value cache
    """
    log.debug('Enter userdb v40->v41 upgrade')
    progress_handler.set_total_steps(1)
    with db.user_write() as write_cursor:
        _add_cache_table(write_cursor)
    progress_handler.new_step()

    log.debug('Finish userdb v40->v41 upgrade')
