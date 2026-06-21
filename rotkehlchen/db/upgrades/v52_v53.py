from typing import TYPE_CHECKING

from rotkehlchen.logging import enter_exit_debug_log
from rotkehlchen.types import Location
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


@enter_exit_debug_log(name='UserDB v52->v53 upgrade')
def upgrade_v52_to_v53(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v52 to v53. This happened in 1.44."""

    @progress_step(description='Create event metrics table and indexes.')
    def _create_event_metrics_table(write_cursor: 'DBCursor') -> None:
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
    def _create_data_issues_table(write_cursor: 'DBCursor') -> None:
        # Hardcoded schema/indexes to prevent future schema changes from affecting this upgrade.
        write_cursor.execute("""
CREATE TABLE IF NOT EXISTS data_issues (
    id INTEGER NOT NULL PRIMARY KEY,
    kind TEXT NOT NULL,
    location TEXT NOT NULL,
    location_label TEXT NOT NULL DEFAULT '',
    protocol TEXT NOT NULL DEFAULT '',
    asset TEXT NOT NULL DEFAULT '',
    event_identifier INTEGER NOT NULL,
    ts_start INTEGER NOT NULL,
    ts_end INTEGER NOT NULL,
    severity TEXT NOT NULL,
    state TEXT NOT NULL,
    auto_remediation_attempts_json TEXT NOT NULL DEFAULT '[]',
    payload_json TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    resolved_at INTEGER,
    UNIQUE(kind, location, location_label, protocol, asset, event_identifier)
);
""")
        write_cursor.executescript("""
CREATE INDEX IF NOT EXISTS idx_data_issues_state ON data_issues(state);
CREATE INDEX IF NOT EXISTS idx_data_issues_kind_state ON data_issues(kind, state);
CREATE INDEX IF NOT EXISTS idx_data_issues_location_label_asset ON data_issues(location, location_label, asset);
""")  # noqa: E501

    @progress_step(description='Add Gate location.')
    def _add_gate_location(write_cursor: 'DBCursor') -> None:
        write_cursor.execute(
            "INSERT OR IGNORE INTO location(location, seq) VALUES ('{', 59);",
        )

    @progress_step(description='Add Bit2me location.')
    def _add_bit2me_location(write_cursor: 'DBCursor') -> None:
        write_cursor.execute(
            "INSERT OR IGNORE INTO location(location, seq) VALUES ('|', 60);",
        )

    @progress_step(description='Normalize exchange history event location labels.')
    def _normalize_exchange_event_location_labels(write_cursor: 'DBCursor') -> None:
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
    def _add_internal_tx_source(write_cursor: 'DBCursor') -> None:
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

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler)
