import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.modules.curve.constants import CPT_CURVE
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HISTORY_MAPPING_STATE_CUSTOMIZED,
    HISTORY_MAPPING_STATE_DECODED,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, make_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.db.dbhandler import DBCursor
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _reset_curve_decoded_events(write_cursor: 'DBCursor') -> None:
    """
    The code is taken from `delete_events_by_tx_hash` right before 1.27 release and is
    modified to delete only transactions that have a decoded curve event.
    """
    query = (
        'SELECT DISTINCT tx_hash from evm_transactions LEFT JOIN history_events '
        'ON history_events.event_identifier=tx_hash INNER JOIN evm_events_info ON '
        'history_events.identifier=evm_events_info.identifier WHERE counterparty IS ?'
    )
    write_cursor.execute(query, (CPT_CURVE,))
    tx_hashes = [x[0] for x in write_cursor]
    write_cursor.execute(
        'SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value=?',
        (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),
    )
    customized_event_ids = [x[0] for x in write_cursor]
    length = len(customized_event_ids)
    querystr = 'DELETE FROM history_events WHERE event_identifier=?'
    if length != 0:
        querystr += f' AND identifier NOT IN ({", ".join(["?"] * length)})'
        bindings = [(x, *customized_event_ids) for x in tx_hashes]
    else:
        bindings = [(x,) for x in tx_hashes]
    write_cursor.executemany(querystr, bindings)
    write_cursor.executemany(
        'DELETE from evm_tx_mappings WHERE tx_hash=? AND chain_id=? AND value=?',
        [(tx_hash, ChainID.ETHEREUM.serialize_for_db(), HISTORY_MAPPING_STATE_DECODED) for tx_hash in tx_hashes],  # noqa: E501
    )


def data_migration_9(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """Introduced at 1.27.1 to address https://github.com/rotki/rotki/issues/5560

    - Add an on-chain locations for events by ethereum and optimism decoders
    - Go through all on-chain history events in the DB and depending on the transaction
    - Remove the obsolete chain_id mappings from history_events_mappings
    hash point location to either ethereum or optimism instead of generic blockchain
    - Remove decoded events with counterparty CURVE
    """
    log.debug('Enter data migration 9')
    progress_handler.set_total_steps(4)
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
        progress_handler.new_step('Remove obsolete chain id mappings')
        write_cursor.execute('DELETE FROM history_events_mappings WHERE name="chain_id"')

        progress_handler.new_step('Remove curve decoded events')
        _reset_curve_decoded_events(write_cursor)

    log.debug('Exit data migration 9')
