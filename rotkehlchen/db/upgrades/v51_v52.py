import logging
import re
from typing import TYPE_CHECKING

from rotkehlchen.chain.bitcoin.bch.validation import is_valid_bitcoin_cash_address
from rotkehlchen.chain.bitcoin.validation import is_valid_btc_address
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import Location
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

NOTES_ADDRESS_MARKER_RE = re.compile(r'\b(?:to|from)\b\s+(.+)$')


def _extract_addresses_from_notes(location: Location, notes: str) -> list[str]:
    if (match := NOTES_ADDRESS_MARKER_RE.search(notes)) is None:
        return []

    validator = is_valid_btc_address if location == Location.BITCOIN else (
        lambda value: is_valid_bitcoin_cash_address(value) or is_valid_btc_address(value)
    )
    return [
        address for entry in match.group(1).split(',')
        if validator(address := entry.strip())
    ]


@enter_exit_debug_log(name='UserDB v51->v52 upgrade')
def upgrade_v51_to_v52(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v51 to v52. This happened in 1.43."""

    @progress_step(description='Create chain event transaction link tables.')
    def _create_chain_event_tx_link_tables(write_cursor: 'DBCursor') -> None:
        write_cursor.executescript("""
        CREATE TABLE IF NOT EXISTS evm_chain_event_txs (
            event_identifier INTEGER NOT NULL PRIMARY KEY,
            tx_id INTEGER NOT NULL,
            FOREIGN KEY(event_identifier)
                REFERENCES chain_events_info(identifier)
                ON UPDATE CASCADE ON DELETE CASCADE,
            FOREIGN KEY(tx_id)
                REFERENCES evm_transactions(identifier)
                ON UPDATE CASCADE ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS solana_chain_event_txs (
            event_identifier INTEGER NOT NULL PRIMARY KEY,
            tx_id INTEGER NOT NULL,
            FOREIGN KEY(event_identifier)
                REFERENCES chain_events_info(identifier)
                ON UPDATE CASCADE ON DELETE CASCADE,
            FOREIGN KEY(tx_id)
                REFERENCES solana_transactions(identifier)
                ON UPDATE CASCADE ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS zksynclite_chain_event_txs (
            event_identifier INTEGER NOT NULL PRIMARY KEY,
            tx_id INTEGER NOT NULL,
            FOREIGN KEY(event_identifier)
                REFERENCES chain_events_info(identifier)
                ON UPDATE CASCADE ON DELETE CASCADE,
            FOREIGN KEY(tx_id)
                REFERENCES zksynclite_transactions(identifier)
                ON UPDATE CASCADE ON DELETE CASCADE
        );
        """)
        write_cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_evm_chain_event_txs_tx_id '
            'ON evm_chain_event_txs(tx_id)',
        )
        write_cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_solana_chain_event_txs_tx_id '
            'ON solana_chain_event_txs(tx_id)',
        )
        write_cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_zksynclite_chain_event_txs_tx_id '
            'ON zksynclite_chain_event_txs(tx_id)',
        )

    @progress_step(description='Backfill chain event transaction links.')
    def _backfill_chain_event_tx_links(write_cursor: 'DBCursor') -> None:
        write_cursor.execute('DELETE FROM evm_chain_event_txs')
        write_cursor.execute('DELETE FROM solana_chain_event_txs')
        write_cursor.execute('DELETE FROM zksynclite_chain_event_txs')
        for location in (
                Location.ETHEREUM,
                Location.OPTIMISM,
                Location.POLYGON_POS,
                Location.ARBITRUM_ONE,
                Location.BASE,
                Location.GNOSIS,
                Location.SCROLL,
                Location.BINANCE_SC,
        ):
            write_cursor.execute(
                'INSERT OR IGNORE INTO evm_chain_event_txs(event_identifier, tx_id) '
                'SELECT C.identifier, T.identifier FROM chain_events_info C '
                'INNER JOIN history_events H ON H.identifier = C.identifier '
                'INNER JOIN evm_transactions T ON T.tx_hash = C.tx_ref AND T.chain_id = ? '
                'WHERE H.location = ?',
                (location.to_chain_id(), location.serialize_for_db()),
            )

        write_cursor.execute(
            'INSERT OR IGNORE INTO solana_chain_event_txs(event_identifier, tx_id) '
            'SELECT C.identifier, T.identifier FROM chain_events_info C '
            'INNER JOIN history_events H ON H.identifier = C.identifier '
            'INNER JOIN solana_transactions T ON T.signature = C.tx_ref '
            'WHERE H.location = ?',
            (Location.SOLANA.serialize_for_db(),),
        )
        write_cursor.execute(
            'INSERT OR IGNORE INTO zksynclite_chain_event_txs(event_identifier, tx_id) '
            'SELECT C.identifier, T.identifier FROM chain_events_info C '
            'INNER JOIN history_events H ON H.identifier = C.identifier '
            'INNER JOIN zksynclite_transactions T ON T.tx_hash = C.tx_ref '
            'WHERE H.location = ?',
            (Location.ZKSYNC_LITE.serialize_for_db(),),
        )
        orphaned_event_ids = {
            row[0] for row in write_cursor.execute(
                'SELECT C.identifier FROM chain_events_info C '
                'INNER JOIN history_events H ON H.identifier = C.identifier '
                'WHERE H.location IN (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) '
                'AND C.identifier NOT IN (SELECT event_identifier FROM evm_chain_event_txs) '
                'AND C.identifier NOT IN (SELECT event_identifier FROM solana_chain_event_txs) '
                'AND C.identifier NOT IN ('
                'SELECT event_identifier FROM zksynclite_chain_event_txs)',
                (
                    Location.ETHEREUM.serialize_for_db(),
                    Location.OPTIMISM.serialize_for_db(),
                    Location.POLYGON_POS.serialize_for_db(),
                    Location.ARBITRUM_ONE.serialize_for_db(),
                    Location.BASE.serialize_for_db(),
                    Location.GNOSIS.serialize_for_db(),
                    Location.SCROLL.serialize_for_db(),
                    Location.BINANCE_SC.serialize_for_db(),
                    Location.SOLANA.serialize_for_db(),
                    Location.ZKSYNC_LITE.serialize_for_db(),
                ),
            )
        }
        if len(orphaned_event_ids) == 0:
            return

        placeholders = ','.join(['?'] * len(orphaned_event_ids))
        write_cursor.execute(
            f'DELETE FROM history_events WHERE identifier IN ({placeholders})',
            tuple(orphaned_event_ids),
        )
        log.warning(
            f'Removed {len(orphaned_event_ids)} on-chain events with missing transactions '
            'during v51->v52 upgrade',
        )

    @progress_step(description='Create bitcoin event address mappings table.')
    def _create_bitcoin_address_mappings_table(write_cursor: 'DBCursor') -> None:
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS bitcoin_events_addresses (
            event_identifier INTEGER NOT NULL,
            address TEXT NOT NULL,
            FOREIGN KEY(event_identifier)
                REFERENCES history_events(identifier)
                ON UPDATE CASCADE ON DELETE CASCADE,
            PRIMARY KEY(event_identifier, address)
        ) WITHOUT ROWID;
        """)
        write_cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_bitcoin_events_addresses_address '
            'ON bitcoin_events_addresses(address)',
        )

    @progress_step(description='Backfill bitcoin event address mappings from notes.')
    def _backfill_bitcoin_address_mappings(write_cursor: 'DBCursor') -> None:
        rows = write_cursor.execute(
            'SELECT identifier, location, notes FROM history_events '
            'WHERE location IN (?, ?) AND notes IS NOT NULL AND type IN (?, ?, ?)',
            (
                Location.BITCOIN.serialize_for_db(),
                Location.BITCOIN_CASH.serialize_for_db(),
                HistoryEventType.SPEND.serialize(),
                HistoryEventType.RECEIVE.serialize(),
                HistoryEventType.TRANSFER.serialize(),
            ),
        ).fetchall()

        mappings: list[tuple[int, str]] = []
        for identifier, location, notes in rows:
            try:
                deserialized_location = Location.deserialize_from_db(location)
            except (ValueError, DeserializationError):
                continue

            mappings.extend([
                (identifier, address)
                for address in _extract_addresses_from_notes(
                    location=deserialized_location,
                    notes=notes,
                )
            ])

        if len(mappings) == 0:
            return

        write_cursor.executemany(
            'INSERT OR IGNORE INTO bitcoin_events_addresses('
            'event_identifier, address'
            ') VALUES(?, ?)',
            mappings,
        )
        log.debug(
            f'Inserted {len(mappings)} bitcoin event address mappings '
            'during v51->v52 upgrade',
        )

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
