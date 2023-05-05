import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def data_migration_8(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """
    Introduced at optimism addition. v1.27.0
    This migration duplicates accounts if active at optimism or avalanche.
    """
    log.debug('Enter data_migration_8')
    with rotki.data.db.conn.read_ctx() as cursor:
        accounts = rotki.data.db.get_blockchain_accounts(cursor)

    # when we sync a remote database the migrations are executed but the chain_manager
    # has not been created yet
    if (chains_aggregator := getattr(rotki, 'chains_aggregator', None)) is not None:
        # steps are: ethereum accounts + potentially write to db
        progress_handler.set_total_steps(len(accounts.eth) + 1)
        chains_aggregator.detect_evm_accounts(progress_handler)

    log.debug('Exit data_migration_8')
