from typing import TYPE_CHECKING

from rotkehlchen.logging import enter_exit_debug_log
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

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler)
