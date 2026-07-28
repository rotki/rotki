import json
import logging
from typing import TYPE_CHECKING

from rotkehlchen.constants.misc import AIRDROPSDIR_NAME, APPDIR_NAME
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.oracles.structures import CurrentPriceOracle
from rotkehlchen.types import Location
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='UserDB v52->v53 upgrade')
def upgrade_v52_to_v53(db: DBHandler, progress_handler: DBUpgradeProgressHandler) -> None:
    """Upgrades the DB from v52 to v53. This happened in 1.44."""

    @progress_step(description='Create event metrics table and indexes.')
    def _create_event_metrics_table(write_cursor: DBCursor) -> None:
        # Hardcoded schema/indexes to prevent future schema changes from affecting this upgrade.
        write_cursor.execute("""
CREATE TABLE IF NOT EXISTS event_metrics (
    id INTEGER NOT NULL PRIMARY KEY,
    event_identifier INTEGER NOT NULL REFERENCES history_events(identifier) ON DELETE CASCADE,
    location CHAR(1) NOT NULL,
    location_label TEXT,
    protocol TEXT,
    metric_key TEXT NOT NULL,
    metric_value TEXT NOT NULL,
    asset TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    sequence_index INTEGER NOT NULL,
    sort_key INTEGER NOT NULL,
    UNIQUE(event_identifier, location_label, protocol, metric_key, asset)
);
""")
        write_cursor.executescript("""
CREATE INDEX IF NOT EXISTS idx_event_metrics_event ON event_metrics(event_identifier);
CREATE INDEX IF NOT EXISTS idx_event_metrics_location_label ON event_metrics(location_label);
CREATE INDEX IF NOT EXISTS idx_event_metrics_protocol ON event_metrics(protocol);
CREATE INDEX IF NOT EXISTS idx_event_metrics_metric_key ON event_metrics(metric_key);
CREATE INDEX IF NOT EXISTS idx_event_metrics_metric_key_timestamp ON event_metrics(metric_key, timestamp);
CREATE INDEX IF NOT EXISTS idx_event_metrics_metric_key_asset_sort_key ON event_metrics(metric_key, asset, sort_key);
CREATE INDEX IF NOT EXISTS idx_event_metrics_asset ON event_metrics(asset);
CREATE INDEX IF NOT EXISTS idx_event_metrics_balances_latest ON event_metrics(metric_key, location, location_label, protocol, asset, timestamp, sort_key, metric_value);
""")  # noqa: E501

    @progress_step(description='Create data issues table and indexes.')
    def _create_data_issues_table(write_cursor: DBCursor) -> None:
        # Hardcoded schema/indexes to prevent future schema changes from affecting this upgrade.
        write_cursor.execute("""
CREATE TABLE IF NOT EXISTS data_issues (
    id INTEGER NOT NULL PRIMARY KEY,
    kind TEXT NOT NULL,
    location TEXT NOT NULL,
    location_label TEXT NOT NULL DEFAULT '',
    protocol TEXT NOT NULL DEFAULT '',
    asset TEXT NOT NULL DEFAULT '',
    event_identifier INTEGER,
    ts_start INTEGER NOT NULL,
    ts_end INTEGER NOT NULL,
    severity TEXT NOT NULL,
    state TEXT NOT NULL,
    auto_remediation_attempts_json TEXT NOT NULL DEFAULT '[]',
    payload_json TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    resolved_at INTEGER
);
""")
        write_cursor.executescript("""
CREATE INDEX IF NOT EXISTS idx_data_issues_state ON data_issues(state);
CREATE INDEX IF NOT EXISTS idx_data_issues_kind_state ON data_issues(kind, state);
CREATE INDEX IF NOT EXISTS idx_data_issues_location_label_asset ON data_issues(location, location_label, asset);
-- `event_identifier` is nullable because some issues are scoped to an event while others are
-- scoped to a bucket. SQLite treats NULL values as distinct in normal UNIQUE constraints, so
-- partial unique indexes are required to enforce one natural key row for both scopes.
CREATE UNIQUE INDEX IF NOT EXISTS unique_data_issues_event_scope ON data_issues(kind, location, location_label, protocol, asset, event_identifier) WHERE event_identifier IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS unique_data_issues_bucket_scope ON data_issues(kind, location, location_label, protocol, asset) WHERE event_identifier IS NULL;
""")  # noqa: E501

    @progress_step(description='Add Gate location.')
    def _add_gate_location(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            "INSERT OR IGNORE INTO location(location, seq) VALUES ('{', 59);",
        )

    @progress_step(description='Add Bit2me location.')
    def _add_bit2me_location(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            "INSERT OR IGNORE INTO location(location, seq) VALUES ('|', 60);",
        )

    @progress_step(description='Add CoinEx location.')
    def _add_coinex_location(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            "INSERT OR IGNORE INTO location(location, seq) VALUES ('}', 61);",
        )

    @progress_step(description='Normalize exchange history event location labels.')
    def _normalize_exchange_event_location_labels(write_cursor: DBCursor) -> None:
        """Normalize exchange labels used as accounting bucket keys.

        If a user has exactly one API key for an exchange and the existing non-NULL event labels
        for that exchange don't indicate mixed keys, NULL labels on that exchange's events can be
        updated to that key name. Existing non-NULL labels are left untouched since they may come
        from CSV imports or removed/dead exchange credentials. Locations with multiple keys are
        intentionally left untouched since assigning old NULL events to a specific key would be
        ambiguous.
        """
        exchange_locations = tuple(location.serialize_for_db() for location in (
            Location.BINANCE,
            Location.BINANCEUS,
            Location.BISQ,
            Location.BITCOINDE,
            Location.BITFINEX,
            Location.BITMEX,
            Location.BITPANDA,
            Location.BITSTAMP,
            Location.BITTREX,
            Location.BLOCKFI,
            Location.BYBIT,
            Location.COINBASE,
            Location.COINBASEPRIME,
            Location.COINBASEPRO,
            Location.CRYPTOCOM,
            Location.FTX,
            Location.FTXUS,
            Location.GEMINI,
            # GATE is omitted because it is first added in this upgrade/release.
            Location.HTX,
            Location.ICONOMI,
            Location.INDEPENDENTRESERVE,
            Location.KRAKEN,
            Location.KUCOIN,
            Location.NEXO,
            Location.OKX,
            Location.POLONIEX,
            Location.SHAPESHIFT,
            Location.UPHOLD,
            Location.WOO,
        ))
        placeholders = ','.join('?' * len(exchange_locations))
        write_cursor.execute(
            'CREATE TEMP TABLE IF NOT EXISTS _exchange_label_fill AS SELECT '
            'user_credentials.location AS location, user_credentials.name AS name FROM '
            'user_credentials WHERE '
            f'user_credentials.location IN ({placeholders}) GROUP BY user_credentials.location '
            'HAVING COUNT(*)=1 AND (SELECT COUNT(DISTINCT history_events.location_label) '
            'FROM history_events WHERE history_events.location=user_credentials.location AND '
            'history_events.location_label IS NOT NULL)<=1',
            exchange_locations,
        )
        write_cursor.execute(
            'UPDATE history_events SET location_label=(SELECT name FROM _exchange_label_fill '
            'WHERE location=history_events.location) WHERE location IN (SELECT location FROM '
            '_exchange_label_fill) AND location_label IS NULL',
        )
        write_cursor.execute('DROP TABLE IF EXISTS _exchange_label_fill')

    @progress_step(description='Persist indexer source for internal transactions.')
    def _add_internal_tx_source(write_cursor: DBCursor) -> None:
        # Track which indexer produced each internal tx row. DEFAULT 0 backfills all
        # existing rows as legacy since source tracking only starts from this upgrade.
        if 'source' not in {
            row[1] for row in write_cursor.execute(
                'PRAGMA table_info(evm_internal_transactions)',
            )
        }:
            write_cursor.execute(
                'ALTER TABLE evm_internal_transactions '
                'ADD COLUMN source INTEGER NOT NULL DEFAULT 0',
            )

    @progress_step(description='Add naming system source to ens mappings.')
    def _add_source_to_ens_mappings(write_cursor: DBCursor) -> None:
        """Store one name per naming system (ENS, GNS, ...) for an address in the
        ens_mappings cache, so that name priority can be applied at read time.
        Existing rows are backfilled as ENS names since that was the only system."""
        if 'source' in {
            row[1] for row in write_cursor.execute('PRAGMA table_info(ens_mappings)')
        }:
            return

        write_cursor.executescript("""
ALTER TABLE ens_mappings RENAME TO ens_mappings_old;
CREATE TABLE ens_mappings (
    address TEXT NOT NULL,
    ens_name TEXT UNIQUE,
    last_update INTEGER NOT NULL,
    last_avatar_update INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'ens',
    PRIMARY KEY(address, source)
);
INSERT INTO ens_mappings(address, ens_name, last_update, last_avatar_update)
SELECT address, ens_name, last_update, last_avatar_update FROM ens_mappings_old;
DROP TABLE ens_mappings_old;
""")

    @progress_step(description='Add Kraken as the first current price oracle.')
    def _add_kraken_current_price_oracle(write_cursor: DBCursor) -> None:
        if (data := write_cursor.execute(
            "SELECT value FROM settings WHERE name='current_price_oracles'",
        ).fetchone()) is None:
            return  # A missing setting uses the defaults, which already have Kraken first.

        try:
            oracles: list[str] = json.loads(data[0])
        except json.JSONDecodeError as e:
            log.error('Failed to read current price oracles from user db due to %s', e)
            return

        kraken = CurrentPriceOracle.KRAKEN.serialize()
        write_cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            (
                'current_price_oracles',
                json.dumps([
                    kraken,
                    *(oracle for oracle in oracles if oracle != kraken),
                ]),
            ),
        )

    @progress_step(description='Removing orphaned history event backups.')
    def _remove_orphaned_event_backups(write_cursor: DBCursor) -> None:
        """Remove backup rows whose event no longer exists. Such backups can never be
        legitimately restored (restore flows find their targets via history_event_links,
        which cascade away with the event), but identifiers (rowids) get reused after
        deletion and save_history_event_backup keeps the earliest row per identifier,
        so a stale backup could later be restored over an unrelated event.
        """
        write_cursor.execute(
            'DELETE FROM history_events_backup WHERE identifier NOT IN '
            '(SELECT identifier FROM history_events)',
        )

    @progress_step(description='Marking exchange adjustment events as synthetic.')
    def _mark_exchange_adjustments_synthetic(write_cursor: DBCursor) -> None:
        """Stamp the auto-created exchange adjustment events with the new SYNTHETIC
        mapping state (5) so they are shown as events manufactured by rotki.

        Scoped to adjustments carrying the MATCHED state (3), which only the asset
        movement matching machinery sets — user-created events of the same type are
        left alone. Hardcoded values to keep the upgrade immune to future changes.
        """
        write_cursor.execute(
            "INSERT OR IGNORE INTO history_events_mappings(parent_identifier, name, value) "
            "SELECT M.parent_identifier, 'state', 5 FROM history_events_mappings M "
            "INNER JOIN history_events H ON H.identifier=M.parent_identifier "
            "WHERE M.name='state' AND M.value=3 AND H.type='exchange adjustment'",
        )

    @progress_step(description='Reset bitcoin transaction query range.')
    def _reset_bitcoin_query_range(write_cursor: DBCursor) -> None:
        """Bitcoin transactions with a change output were decoded as a spend of the entire
        input plus a receive of the change, inventing a disposal and an acquisition that
        never happened and corrupting cost basis. Transfers between owned addresses were
        also never credited to the receiving address in historical balances.

        Unlike EVM and Solana, raw bitcoin transactions are not stored locally, so they
        cannot be redecoded offline here. Instead reset the per-address last queried block,
        so the next transaction query refetches the full history from the explorers and
        decodes it with the corrected logic.

        The existing events are deliberately left in place rather than deleted here. The
        query purges each transaction's events right before writing the new ones, so they
        are replaced one transaction at a time and the user keeps a visible history in the
        meantime. That purge is keyed on the group identifier, so it also clears the mixed
        stale/new event sets left by the sequence index collisions this same release fixes.
        """
        write_cursor.execute(
            "DELETE FROM key_value_cache WHERE "
            "name LIKE 'last\\_btc\\_tx\\_block\\_%' ESCAPE '\\' OR "
            "name LIKE 'last\\_bch\\_tx\\_block\\_%' ESCAPE '\\'",
        )

    @progress_step(description='Remove obsolete airdrop parquet files.')
    def _remove_airdrop_parquet_files(write_cursor: DBCursor) -> None:
        """Remove parquet airdrop files left behind now that airdrops use compressed CSV files."""
        for parquet_file_path in (
            db.user_data_dir.parent.parent / APPDIR_NAME / AIRDROPSDIR_NAME
        ).glob('*.parquet'):
            try:
                parquet_file_path.unlink()
            except OSError as e:
                log.error(
                    'Failed to remove airdrop file %s due to %s. Skipping it',
                    parquet_file_path,
                    e,
                )

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler)
