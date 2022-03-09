"""Begin Database Schema for Transient Database"""

# Transient table for recording PnL reports
DB_CREATE_PNL_REPORT = """
CREATE TABLE IF NOT EXISTS pnl_reports (
    identifier INTEGER NOT NULL PRIMARY KEY,
    timestamp INTEGER,
    start_ts INTEGER,
    end_ts INTEGER,
    first_processed_timestamp INTEGER,
    last_processed_timestamp INTEGER NOT NULL,
    processed_actions INTEGER NOT NULL,
    total_actions INTEGER NOT NULL
);
"""

DB_CREATE_REPORT_TOTALS = """
CREATE TABLE IF NOT EXISTS pnl_report_totals (
    report_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    FOREIGN KEY (report_id) REFERENCES pnl_reports(identifier) ON DELETE CASCADE ON UPDATE CASCADE,
    PRIMARY KEY(report_id, name)
);
"""

DB_CREATE_REPORT_SETTINGS = """
CREATE TABLE IF NOT EXISTS pnl_report_settings (
    report_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    value TEXT NOT NULL,
    FOREIGN KEY (report_id) REFERENCES pnl_reports(identifier) ON DELETE CASCADE ON UPDATE CASCADE,
    PRIMARY KEY(report_id, name)
);
"""

# Custom enum table accounting event types
DB_CREATE_ACCOUNTING_EVENT_TYPE = """
CREATE TABLE IF NOT EXISTS accounting_event_type (
  type    CHAR(1)       PRIMARY KEY NOT NULL,
  seq     INTEGER UNIQUE
);
/* Income Action Type */
INSERT OR IGNORE INTO accounting_event_type(type, seq) VALUES ('A', 1);
"""

# Many records for events related through foreign key to each PnL report.
DB_CREATE_PNL_EVENTS = """
CREATE TABLE IF NOT EXISTS pnl_events (
    identifier INTEGER NOT NULL PRIMARY KEY,
    report_id INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    event_type CHAR(1) NOT NULL DEFAULT('A') REFERENCES accounting_event_type(type),
    data TEXT NOT NULL,
    FOREIGN KEY (report_id) REFERENCES pnl_reports(identifier) ON DELETE CASCADE ON UPDATE CASCADE
);
"""

DB_CREATE_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    name VARCHAR[24] NOT NULL PRIMARY KEY,
    value TEXT
);
"""

DB_SCRIPT_CREATE_TRANSIENT_TABLES = f"""
PRAGMA foreign_keys=off;
BEGIN TRANSACTION;
{DB_CREATE_PNL_REPORT}
{DB_CREATE_REPORT_SETTINGS}
{DB_CREATE_REPORT_TOTALS}
{DB_CREATE_ACCOUNTING_EVENT_TYPE}
{DB_CREATE_PNL_EVENTS}
{DB_CREATE_SETTINGS}
COMMIT;
PRAGMA foreign_keys=on;
"""
