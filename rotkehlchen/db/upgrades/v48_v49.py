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


@enter_exit_debug_log(name='UserDB v48->v49 upgrade')
def upgrade_v48_to_v49(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v48 to v49. This is expected to be in v1.40 release.

    - Fix zksynclite_swaps table schema: change TEXT_NOT NULL to TEXT NOT NULL for to_amount column
    """
    @progress_step(description='Fixing zksynclite_swaps table schema.')
    def _fix_zksynclite_swaps_schema(write_cursor: 'DBCursor') -> None:
        # First check if the table exists and if it has any data
        if write_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='zksynclite_swaps'").fetchone() is None:  # noqa: E501
            log.debug('zksynclite_swaps table does not exist, skipping upgrade')
            return

        # Get the current schema to verify if we need to fix it
        schema_info = write_cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='zksynclite_swaps'").fetchone()  # noqa: E501
        if schema_info and 'TEXT_NOT NULL' not in schema_info[0]:
            log.debug('zksynclite_swaps table does not have the TEXT_NOT NULL bug, skipping')
            return

        # Create a temporary table with the correct schema
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS zksynclite_swaps_new (
            tx_id INTEGER NOT NULL,
            from_asset TEXT NOT NULL,
            from_amount TEXT NOT NULL,
            to_asset TEXT NOT NULL,
            to_amount TEXT NOT NULL,
            FOREIGN KEY(tx_id) REFERENCES zksynclite_transactions(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
            FOREIGN KEY(from_asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
            FOREIGN KEY(to_asset) REFERENCES assets(identifier) ON UPDATE CASCADE
        );
        """)

        # Copy data from the old table, converting any NULL to_amount values to '0'
        write_cursor.execute("""
        INSERT INTO zksynclite_swaps_new (tx_id, from_asset, from_amount, to_asset, to_amount)
        SELECT tx_id, from_asset, from_amount, to_asset, 
               CASE WHEN to_amount IS NULL THEN '0' ELSE to_amount END
        FROM zksynclite_swaps;
        """)

        # Drop the old table and rename the new one
        write_cursor.execute('DROP TABLE zksynclite_swaps;')
        write_cursor.execute('ALTER TABLE zksynclite_swaps_new RENAME TO zksynclite_swaps;')

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=False)