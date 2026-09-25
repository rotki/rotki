from typing import TYPE_CHECKING

from rotkehlchen.logging import enter_exit_debug_log

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen


@enter_exit_debug_log()
def data_migration_28(rotki: Rotkehlchen, progress_handler: MigrationProgressHandler) -> None:
    """Make legacy zero L1 fees repairable; only newly resolved zeros remain stored as zero."""
    progress_handler.set_total_steps(1)
    progress_handler.new_step('Marking legacy zero L1 fees as unresolved')
    with rotki.data.db.user_write() as write_cursor:
        write_cursor.execute("UPDATE optimism_transactions SET l1_fee=NULL WHERE l1_fee='0'")
