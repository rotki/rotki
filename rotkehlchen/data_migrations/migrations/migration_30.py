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

    perform_userdb_migration_steps(rotki, progress_handler, should_vacuum=False)
