"""Begin Database Schema for Transient Database"""

# Transient table for recording PnL reports
DB_CREATE_PNL_REPORT = """
CREATE TABLE IF NOT EXISTS pnl_reports (
    identifier INTEGER NOT NULL PRIMARY KEY,
    name TEXT,
    timestamp INTEGER,
    start_ts INTEGER,
    end_ts INTEGER,
    overview TEXT,
    first_processed_timestamp INTEGER,
    events_processed INTEGER,
    size_on_disk INTEGER
);
"""

# Many records for events related through foreign key to each PnL report.
DB_CREATE_PNL_EVENTS = """
CREATE TABLE IF NOT EXISTS pnl_events (
    identifier INTEGER NOT NULL PRIMARY KEY,
    report_id INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    data TEXT NOT NULL,
    FOREIGN KEY (report_id) REFERENCES pnl_reports(identifier) ON DELETE CASCADE ON UPDATE CASCADE
);
"""

DB_SCRIPT_CREATE_TRANSIENT_TABLES = f"""
PRAGMA foreign_keys=off;
BEGIN TRANSACTION;
{DB_CREATE_PNL_REPORT}
{DB_CREATE_PNL_EVENTS}
COMMIT;
PRAGMA foreign_keys=on;
"""
