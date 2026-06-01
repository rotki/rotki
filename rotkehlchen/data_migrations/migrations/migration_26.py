from typing import TYPE_CHECKING

from rotkehlchen.logging import enter_exit_debug_log
from rotkehlchen.utils.progress import perform_userdb_migration_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen


@enter_exit_debug_log()
def data_migration_26(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """Introduced at v1.43.2

    Clean up manually tracked balance tag mappings that were orphaned by the v51->v52 DB
    upgrade. That upgrade rebuilt manually_tracked_balances without preserving the id column,
    so rows above a deleted-id gap were renumbered and their tag_mappings (keyed by the old id)
    no longer point at any balance. Worse, since ids are now dense, a stale mapping can later
    re-attach to a newly added balance that happens to reuse the old id, showing a phantom tag.

    The original association is unrecoverable, so we delete the orphaned mappings. Manual balance
    tags use a pure-integer object_reference (blockchain accounts use addresses and xpubs use the
    xpub string), so all-digit references that match no current balance id are the orphans.
    """
    @progress_step(description='Removing orphaned manual balance tag mappings')
    def _remove_orphaned_manual_balance_tags(rotki: 'Rotkehlchen') -> None:
        with rotki.data.db.conn.write_ctx() as write_cursor:
            write_cursor.execute(
                'DELETE FROM tag_mappings WHERE '
                "object_reference GLOB '[0-9]*' AND NOT object_reference GLOB '*[^0-9]*' AND "
                'CAST(object_reference AS INTEGER) NOT IN (SELECT id FROM manually_tracked_balances)',  # noqa: E501
            )

    perform_userdb_migration_steps(rotki, progress_handler, should_vacuum=False)
