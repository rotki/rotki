import logging
from typing import TYPE_CHECKING

from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log()
def data_migration_16(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:  # pylint: disable=unused-argument
    """Introduced at v1.34.2

    Removes the underlying token entries from the database that have themselves
    as the underlying token."""
    progress_handler.set_total_steps(1)
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'DELETE FROM underlying_tokens_list WHERE identifier=parent_token_entry;',
        )

    progress_handler.new_step()
