from typing import TYPE_CHECKING

from rotkehlchen.logging import enter_exit_debug_log
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


@enter_exit_debug_log(name='globaldb v11->v12 upgrade')
def migrate_to_v12(connection: 'DBConnection', progress_handler: 'DBUpgradeProgressHandler') -> None:  # noqa: E501
    """This globalDB upgrade does the following:
    - Add new table for counterparty mappings

    This upgrade takes place in v1.39.0"""
    @progress_step('Adding new tables.')
    def _create_new_tables(write_cursor: 'DBCursor') -> None:
        write_cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS counterparty_asset_mappings (
                counterparty TEXT NOT NULL,
                symbol TEXT NOT NULL,
                local_id TEXT NOT NULL COLLATE NOCASE,
                PRIMARY KEY (counterparty, symbol)
            );
            """,
        )

    perform_globaldb_upgrade_steps(connection, progress_handler)
