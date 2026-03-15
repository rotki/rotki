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

    @progress_step(description='Clean duplicated internal tx rows with legacy gas values.')
    def _cleanup_legacy_internal_txs(write_cursor: 'DBCursor') -> None:
        """Remove legacy all zero gas internal tx rows after repulls inserted corrected rows.

        Legacy rows are identified as entries with gas=0 and gas_used=0 created by a previous
        schema migration default. If a row with the same parent/from/to/value exists and has
        non legacy gas data, the legacy row is considered a duplicate and removed.

        We skip the trace id in the comparassion because it can lead to error.
        """
        duplicate_legacy_rows_query = """
            SELECT legacy.rowid, legacy.parent_tx
            FROM evm_internal_transactions AS legacy
            WHERE legacy.gas = '0'
              AND legacy.gas_used = '0'
              AND EXISTS (
                  SELECT 1
                  FROM evm_internal_transactions AS corrected
                  WHERE corrected.parent_tx = legacy.parent_tx
                    AND corrected.from_address = legacy.from_address
                    AND corrected.to_address IS legacy.to_address
                    AND corrected.value = legacy.value
                    AND (corrected.gas != '0' OR corrected.gas_used != '0')
              )
        """
        affected_parent_hashes = [
            f'0x{entry[0]}'
            for entry in write_cursor.execute(
                f"""
                SELECT DISTINCT lower(hex(evm_transactions.tx_hash))
                FROM ({duplicate_legacy_rows_query}) AS duplicates
                JOIN evm_transactions
                    ON evm_transactions.identifier = duplicates.parent_tx
                ORDER BY evm_transactions.identifier
                """,
            ).fetchall()
        ]
        write_cursor.execute(
            f"""
            DELETE FROM evm_internal_transactions
            WHERE rowid IN (SELECT rowid FROM ({duplicate_legacy_rows_query}))
            """,
        )
        log.debug(
            f'Removed {write_cursor.rowcount} duplicated internal tx rows with '
            f'legacy gas values in v51->v52 upgrade. Parent hashes: {affected_parent_hashes}',
        )

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
