import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log()
def data_migration_17(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:  # pylint: disable=unused-argument
    """
    Introduced at v1.34.3

    Add 4 new locations to the DB
    """
    progress_handler.set_total_steps(1)
    with rotki.data.db.conn.write_ctx() as write_cursor:
        write_cursor.executescript("""
        /* Bitcoin */
        INSERT OR IGNORE INTO location(location, seq) VALUES ('q', 49);
        /* Bitcoin Cash */
        INSERT OR IGNORE INTO location(location, seq) VALUES ('r', 50);
        /* Polkadot */
        INSERT OR IGNORE INTO location(location, seq) VALUES ('s', 51);
        /* Kusama */
        INSERT OR IGNORE INTO location(location, seq) VALUES ('t', 52);
        """)

    progress_handler.new_step()
