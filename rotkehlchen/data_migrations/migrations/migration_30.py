import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.solana.constants import SOLANA_V1_ACTIVATION_SLOT
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import SolanaAddress, SupportedBlockchain
from rotkehlchen.utils.progress import perform_userdb_migration_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log()
def data_migration_30(rotki: Rotkehlchen, progress_handler: MigrationProgressHandler) -> None:
    """Introduced at v1.44.3.

    Solana v1 transactions were skipped while querying transaction details. Mark accounts whose
    stored history has already advanced past v1 activation so their affected interval is backfilled
    during the next normal transaction sync. The migration itself performs no network requests.

    It also removes the last balances query timestamp of chains that are fully disabled in
    disabled_chain_queries. Nothing refreshes it while the chain is disabled, so the one it had
    when it was disabled was still reported as its last refresh.
    """
    @progress_step(description='Scheduling missing Solana v1 transaction recovery')
    def _schedule_solana_transaction_backfill(rotki: Rotkehlchen) -> None:
        with rotki.data.db.conn.read_ctx() as cursor:
            accounts = [SolanaAddress(row[0]) for row in cursor.execute(
                'SELECT ba.account FROM blockchain_accounts ba '
                'WHERE ba.blockchain=? AND EXISTS('
                'SELECT 1 FROM solana_transactions st '
                'JOIN solanatx_address_mappings sam ON st.identifier=sam.tx_id '
                'WHERE st.slot >= ? AND (sam.address=ba.account OR sam.address IN ('
                'SELECT ata_address FROM solana_ata_address_mappings WHERE account=ba.account)))',
                (SupportedBlockchain.SOLANA.value, SOLANA_V1_ACTIVATION_SLOT),
            )]

        with rotki.data.db.user_write() as write_cursor:
            write_cursor.executemany(
                'INSERT OR IGNORE INTO key_value_cache(name, value) VALUES(?, ?)',
                [(
                    DBCacheDynamic.SOLANA_TX_BACKFILL_FROM_SLOT.get_db_key(address=account),
                    SOLANA_V1_ACTIVATION_SLOT,
                ) for account in accounts],
            )

    @progress_step(description='Removing stale balance refresh times of disabled chains')
    def _delete_stale_balances_query_timestamps(rotki: Rotkehlchen) -> None:
        with rotki.data.db.conn.read_ctx() as cursor:
            disabled_chain_queries = rotki.data.db.get_settings(cursor).disabled_chain_queries

        with rotki.data.db.user_write() as write_cursor:
            rotki.data.db.delete_balances_query_ts_for_disabled_chains(
                write_cursor=write_cursor,
                disabled_chain_queries=disabled_chain_queries,
            )

    perform_userdb_migration_steps(rotki, progress_handler, should_vacuum=False)
