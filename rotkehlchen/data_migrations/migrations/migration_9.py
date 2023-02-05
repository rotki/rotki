import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import make_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def data_migration_9(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """Introduced at 1.27.1 to address https://github.com/rotki/rotki/issues/5560

    - Add an on-chain locations for events by ethereum and optimism decoders
    - Go through all on-chain history events in the DB and depending on the transaction
    hash point location to either ethereum or optimism instead of generic blockchain
    """
    log.debug('Enter data migration 9')
    progress_handler.set_total_steps(2)
    progress_handler.new_step('Add two new locations')
    with rotki.data.db.conn.write_ctx() as write_cursor:
        write_cursor.execute('INSERT OR IGNORE INTO location(location, seq) VALUES ("f", 38);')
        write_cursor.execute('INSERT OR IGNORE INTO location(location, seq) VALUES ("g", 39);')

    progress_handler.new_step('Add proper location to decoded events')
    with rotki.data.db.conn.read_ctx() as cursor:
        cursor.execute(
            'SELECT chain_id, tx_hash FROM evm_transactions WHERE '
            'tx_hash IN (SELECT event_identifier FROM history_events)',
        )
        update_tuples = []
        for chain_id, tx_hash in cursor:
            if chain_id == 1:
                location = 'f'  # ethereum
            elif chain_id == 10:
                location = 'g'  # optimism
            else:  # unexpected -- skip entry from editing
                log.error(
                    f'Found unexpected chain id {chain_id} in the DB for transaction '
                    f'{make_evm_tx_hash(tx_hash).hex()}',  # pylint: disable=no-member
                )
                continue

            update_tuples.append((location, tx_hash))

    with rotki.data.db.conn.write_ctx() as write_cursor:
        write_cursor.executemany(
            'UPDATE history_events SET location=? WHERE event_identifier=?', update_tuples,
        )

    log.debug('Exit data migration 9')
