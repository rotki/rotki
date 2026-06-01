import logging
import re
from typing import TYPE_CHECKING

from rotkehlchen.chain.bitcoin.bch.validation import is_valid_bitcoin_cash_address
from rotkehlchen.chain.bitcoin.validation import is_valid_btc_address
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HistoryMappingState
from rotkehlchen.db.utils import update_table_schema
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
BLOCKSCOUT_SERVICES_TO_DELETE = (
    'blockscout',
    'optimism_blockscout',
    'polygon_pos_blockscout',
    'arbitrum_one_blockscout',
    'base_blockscout',
    'gnosis_blockscout',
    'hyperliquid_blockscout',
    'scroll_blockscout',
)


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

    @progress_step(description='Create blockchain balances cache table.')
    def _create_blockchain_balances_cache_table(write_cursor: 'DBCursor') -> None:
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS blockchain_balances_cache (
            blockchain TEXT NOT NULL,
            address TEXT NOT NULL,
            asset TEXT NOT NULL,
            label TEXT NOT NULL DEFAULT '',
            category CHAR(1) NOT NULL DEFAULT('A'),
            amount TEXT NOT NULL,
            FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
            PRIMARY KEY (blockchain, address, asset, label, category)
        ) WITHOUT ROWID;
        """)

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

    @progress_step(description='Adding Hyperliquid and Monad location to the DB.')
    def _add_locations(write_cursor: 'DBCursor') -> None:
        write_cursor.executemany(
            'INSERT OR IGNORE INTO location(location, seq) VALUES (?, ?)',
            (
                (Location.HYPERLIQUID.serialize_for_db(), 57),
                (Location.MONAD.serialize_for_db(), 58),
            ),
        )

    @progress_step(description='Adding UNIQUE constraint to manually_tracked_balances label column.')  # noqa: E501
    def _add_unique_label_constraint(write_cursor: 'DBCursor') -> None:
        """Add UNIQUE constraint to the label column of manually_tracked_balances.
        First deduplicate any existing entries by appending a suffix.
        """
        duplicates = write_cursor.execute(
            'SELECT label FROM manually_tracked_balances '
            'GROUP BY label HAVING COUNT(*) > 1',
        ).fetchall()

        for (label,) in duplicates:
            rows = write_cursor.execute(
                'SELECT id FROM manually_tracked_balances WHERE label=? ORDER BY id',
                (label,),
            ).fetchall()
            for idx, (row_id,) in enumerate(rows[1:], start=2):
                write_cursor.execute(
                    'UPDATE manually_tracked_balances SET label=? WHERE id=?',
                    (f'{label} ({idx})', row_id),
                )

        # Preserve the id column when it exists so tag_mappings (which reference
        # manually_tracked_balances.id) are not orphaned by a rowid renumbering. Some older DBs
        # may predate the id column, so detect it instead of assuming it is present.
        has_id = any(
            row[1] == 'id'
            for row in write_cursor.execute('PRAGMA table_info(manually_tracked_balances)')
        )
        columns = ('id, ' if has_id else '') + 'asset, label, amount, location, category'
        write_cursor.switch_foreign_keys('OFF')
        update_table_schema(
            write_cursor=write_cursor,
            table_name='manually_tracked_balances',
            schema="""id INTEGER PRIMARY KEY,
            asset TEXT NOT NULL,
            label TEXT NOT NULL UNIQUE,
            amount TEXT,
            location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
            category CHAR(1) NOT NULL DEFAULT('A') REFERENCES balance_category(category),
            FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE""",
            insert_columns=columns,
            insert_order=f'({columns})',
        )
        write_cursor.switch_foreign_keys('ON')

    @progress_step(description='Deleting legacy blockscout api key credentials.')
    def _delete_legacy_blockscout_credentials(write_cursor: 'DBCursor') -> None:
        write_cursor.executemany(
            'DELETE FROM external_service_credentials WHERE name=?',
            [(service_name,) for service_name in BLOCKSCOUT_SERVICES_TO_DELETE],
        )

    @progress_step(description='Resetting decoded events.')
    def _reset_decoded_events(write_cursor: 'DBCursor') -> None:
        """Reset all decoded evm and solana events except those in zksync lite.
        If any event in a transaction is customized, all events in that transaction
        are preserved along with its decoded status.
        """
        if (
            write_cursor.execute('SELECT COUNT(*) FROM evm_transactions').fetchone()[0] > 0 or
            write_cursor.execute('SELECT COUNT(*) FROM solana_transactions').fetchone()[0] > 0
        ):
            querystr = (
                "DELETE FROM history_events WHERE identifier IN ("
                "SELECT H.identifier FROM history_events H INNER JOIN chain_events_info C "
                "ON H.identifier=C.identifier AND (C.tx_ref IN "
                "(SELECT tx_hash FROM evm_transactions) OR C.tx_ref IN "
                "(SELECT signature FROM solana_transactions)) AND H.location != 'o')"  # location 'o' is zksync lite  # noqa: E501
            )
            bindings: tuple = ()
            has_customized = write_cursor.execute(
                'SELECT COUNT(*) FROM history_events_mappings WHERE name=? AND value=?',
                (customized_events_bindings := (HISTORY_MAPPING_KEY_STATE, HistoryMappingState.CUSTOMIZED.serialize_for_db())),  # noqa: E501
            ).fetchone()[0] != 0
            if has_customized:
                querystr += (
                    ' AND group_identifier NOT IN ('
                    'SELECT H2.group_identifier FROM history_events H2 '
                    'INNER JOIN history_events_mappings M ON H2.identifier = M.parent_identifier '
                    'WHERE M.name=? AND M.value=?)'
                )
                bindings = customized_events_bindings

            write_cursor.execute(querystr, bindings)
            for table, tx_table, tx_id_col in (
                ('evm_tx_mappings', 'evm_transactions', 'tx_hash'),
                ('solana_tx_mappings', 'solana_transactions', 'signature'),
            ):
                tx_querystr = (
                    f'DELETE FROM {table} WHERE tx_id IN '
                    f'(SELECT identifier FROM {tx_table}) AND value=?'
                )
                tx_bindings: tuple = (0,)  # decoded tx state
                if has_customized:
                    tx_querystr += (
                        f' AND tx_id NOT IN ('
                        f'SELECT DISTINCT T.identifier FROM {tx_table} T '
                        f'INNER JOIN chain_events_info C ON T.{tx_id_col} = C.tx_ref '
                        'INNER JOIN history_events_mappings M ON C.identifier = M.parent_identifier '  # noqa: E501
                        'WHERE M.name=? AND M.value=?)'
                    )
                    tx_bindings += customized_events_bindings
                write_cursor.execute(tx_querystr, tx_bindings)

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
