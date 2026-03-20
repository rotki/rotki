from typing import TYPE_CHECKING

from rotkehlchen.db.internal_tx_conflicts import (
    INTERNAL_TX_CONFLICT_ACTION_FIX_REDECODE,
    POPULATE_INTERNAL_TX_CONFLICTS_QUERY,
    clean_internal_tx_conflict,
    get_internal_tx_conflicts,
    is_tx_customized,
    set_internal_tx_conflict_fixed,
)
from rotkehlchen.db.schema import DB_CREATE_EVM_INTERNAL_TX_CONFLICTS
from rotkehlchen.logging import enter_exit_debug_log
from rotkehlchen.utils.progress import perform_userdb_migration_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen


@enter_exit_debug_log()
def data_migration_24(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """Introduced at v1.42.1
    - Create and populate internal tx conflict queue
    - Locally fix non-customized fix_redecode conflicts and queue txs for redecoding
    """
    @progress_step(description='Creating internal tx conflict table and indexes')
    def _create_table(rotki: 'Rotkehlchen') -> None:
        with rotki.data.db.conn.write_ctx() as write_cursor:
            write_cursor.execute(DB_CREATE_EVM_INTERNAL_TX_CONFLICTS)
            write_cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_chain_events_info_tx_ref '
                'ON chain_events_info(tx_ref)',
            )

    @progress_step(description='Populating internal tx conflicts')
    def _populate_conflicts(rotki: 'Rotkehlchen') -> None:
        with rotki.data.db.conn.write_ctx() as write_cursor:
            write_cursor.execute(POPULATE_INTERNAL_TX_CONFLICTS_QUERY)

    @progress_step(description='Fixing non-customized internal tx conflicts')
    def _fix_non_customized(rotki: 'Rotkehlchen') -> None:
        with rotki.data.db.conn.write_ctx() as write_cursor:
            for chain_id, tx_hash, _ in get_internal_tx_conflicts(
                cursor=write_cursor,
                action=INTERNAL_TX_CONFLICT_ACTION_FIX_REDECODE,
                fixed=False,
            ):
                if is_tx_customized(write_cursor, tx_hash=tx_hash, chain_id=chain_id):
                    continue

                clean_internal_tx_conflict(
                    write_cursor=write_cursor,
                    tx_hash=tx_hash,
                    chain_id=chain_id,
                )
                set_internal_tx_conflict_fixed(
                    write_cursor=write_cursor,
                    tx_hash=tx_hash,
                    chain_id=chain_id,
                )

    perform_userdb_migration_steps(rotki, progress_handler, should_vacuum=False)
