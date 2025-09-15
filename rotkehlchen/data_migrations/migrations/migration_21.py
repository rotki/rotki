from typing import TYPE_CHECKING

from rotkehlchen.data_migrations.common import migrate_addressbook_none_to_ecosystem_key
from rotkehlchen.logging import enter_exit_debug_log
from rotkehlchen.utils.progress import perform_userdb_migration_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen


@enter_exit_debug_log()
def data_migration_21(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """Introduced at v1.40.1
    Replace 'NONE' blockchain marker in user address_book with ecosystem-specific key.
    """

    @progress_step(description='Upgrading adderess book ecosystem names')
    def _migrate_ecosystem_names(rotki: 'Rotkehlchen') -> None:
        migrate_addressbook_none_to_ecosystem_key(
            connection=rotki.data.db.conn,
            msg_aggregator=rotki.msg_aggregator,
        )

    perform_userdb_migration_steps(rotki, progress_handler, should_vacuum=True)
