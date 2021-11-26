"""Begin Database Schema for Transient Database"""

# Transient table for recording PnL reports
DB_CREATE_PNL_REPORT = """
CREATE TABLE IF NOT EXISTS pnl_reports (
    identifier INTEGER NOT NULL PRIMARY KEY,
    timestamp INTEGER,
    start_ts INTEGER,
    end_ts INTEGER,
    first_processed_timestamp INTEGER,
    ledger_actions_profit_loss TEXT,
    defi_profit_loss TEXT,
    loan_profit TEXT,
    margin_positions_profit_loss TEXT,
    settlement_losses TEXT,
    ethereum_transaction_gas_costs TEXT,
    asset_movement_fees TEXT,
    general_trade_profit_loss TEXT,
    taxable_trade_profit_loss TEXT,
    total_taxable_profit_loss TEXT,
    total_profit_loss TEXT
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

DB_SCRIPT_CREATE_TRANSIENT_TABLES = f"""
PRAGMA foreign_keys=off;
BEGIN TRANSACTION;
{DB_CREATE_PNL_REPORT}
{DB_CREATE_ACCOUNTING_EVENT_TYPE}
{DB_CREATE_PNL_EVENTS}
COMMIT;
PRAGMA foreign_keys=on;
"""
