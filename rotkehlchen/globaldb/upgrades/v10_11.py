from typing import TYPE_CHECKING

from rotkehlchen.logging import enter_exit_debug_log
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


@enter_exit_debug_log(name='globaldb v10->v11 upgrade')
def migrate_to_v11(connection: 'DBConnection', progress_handler: 'DBUpgradeProgressHandler') -> None:  # noqa: E501
    """This globalDB upgrade does the following:

    1. Adds alchemy to the historical price sources table.

    This upgrade took place in v1.38
    """

    @progress_step('Adding alchemy to price_history_source_types')
    def update_price_history_source_types_entries(write_cursor: 'DBCursor') -> None:
        write_cursor.execute(
            'INSERT INTO price_history_source_types(type, seq) VALUES (?, ?)',
            ('I', 9),
        )

    perform_globaldb_upgrade_steps(
        connection=connection,
        progress_handler=progress_handler,
        should_vacuum=True,
    )
