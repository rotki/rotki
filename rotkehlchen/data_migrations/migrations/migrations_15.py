import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.hop.constants import CPT_HOP
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HISTORY_MAPPING_STATE_CUSTOMIZED,
    HISTORY_MAPPING_STATE_DECODED,
)
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import SUPPORTED_CHAIN_IDS, ChainID, Location, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log()
def data_migration_15(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """Introduced at v1.34.1

    Redecodes the distinct Add liquidity events for each Hop LP token."""
    progress_handler.set_total_steps(1)
    # find one Add liquidity event for each Hop LP token
    with rotki.data.db.conn.read_ctx() as cursor:
        event_data = [
            (
                identifier,
                deserialize_evm_tx_hash(db_tx_hash),
                Location.deserialize_from_db(db_location),
            )
            for identifier, db_tx_hash, db_location in cursor.execute(
                'SELECT EE.identifier, tx_hash, location FROM evm_events_info AS EE '
                'LEFT JOIN history_events as HE on HE.identifier=EE.identifier '
                'WHERE counterparty=? AND type=? AND subtype=? AND EE.identifier NOT IN ('
                'SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value=?'
                ') GROUP BY asset;', (
                    CPT_HOP,
                    HistoryEventType.RECEIVE.serialize(),
                    HistoryEventSubType.RECEIVE_WRAPPED.serialize(),
                    HISTORY_MAPPING_KEY_STATE,
                    HISTORY_MAPPING_STATE_CUSTOMIZED,
                ),
            )
        ]

    with rotki.data.db.conn.write_ctx() as write_cursor:  # delete their events
        for identifier, _, _ in event_data:
            write_cursor.execute('DELETE FROM history_events WHERE identifier=?', (identifier,))
            write_cursor.execute(
                'DELETE from evm_tx_mappings WHERE tx_id=? AND value=?',
                (identifier, HISTORY_MAPPING_STATE_DECODED),
            )

    for _, tx_hash, location in event_data:  # redecode them
        chain_id: SUPPORTED_CHAIN_IDS = ChainID.deserialize(location.to_chain_id())  # type: ignore[assignment]  # db_location is already decoded, so it's supported
        chain_manager = rotki.chains_aggregator.get_evm_manager(chain_id=chain_id)
        try:
            chain_manager.transactions_decoder.decode_transaction_hashes(
                tx_hashes=[tx_hash],
                ignore_cache=True,  # always redecode from here
            )
        except (RemoteError, DeserializationError, InputError) as e:
            log.error(
                f'Failed to decode evm transaction due to {e!s} for tx_hash {tx_hash!s} '
                f'while doing data migration 15',
            )
            continue

    progress_handler.new_step()
