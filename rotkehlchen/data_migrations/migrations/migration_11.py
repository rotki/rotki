import logging
from typing import TYPE_CHECKING

from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _get_optimism_transaction_fees(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:  # noqa: E501
    """Since we now need 1 extra column per optimism transaction we need to repull all
    optimism transactions to store the l1 gas fee"""
    if (chains_aggregator := getattr(rotki, 'chains_aggregator', None)) is None:
        return  # if sync a DB from the server and migration is needed, aggregator is not yet initialized  # noqa: E501

    with rotki.data.db.conn.read_ctx() as cursor:
        cursor.execute('SELECT tx_hash, identifier FROM evm_transactions WHERE chain_id=10')
        txhash_to_id = dict(cursor)

    progress_handler.set_total_steps(len(txhash_to_id))

    db_tuples = []
    optimism_manager = chains_aggregator.get_evm_manager(ChainID.OPTIMISM)
    assert optimism_manager, 'should exist at this point'
    for txhash, txid in txhash_to_id.items():
        progress_handler.new_step(f'Fetching optimism transaction {txhash.hex()}')
        try:
            transaction, _ = optimism_manager.node_inquirer.get_transaction_by_hash(tx_hash=txhash)
        except RemoteError:
            log.error(f'Could not pull data from optimism for transaction {txhash.hex()}')
            continue

        db_tuples.append((txid, str(transaction.l1_fee)))

    with rotki.data.db.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT OR IGNORE INTO optimism_transactions(tx_id, l1_fee) VALUES(?, ?)',
            db_tuples,
        )


def data_migration_11(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """
    Introduced at v1.30.0
    """
    log.debug('Enter data_migration_11')
    _get_optimism_transaction_fees(rotki, progress_handler)
    log.debug('Exit data_migration_11')
