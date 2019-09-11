"""
For DB upgrade testing purposes need to keep the old create DB scripts here
until v5. Since can't find old DBs to test with.

From now and on for all upgrade tests we should use old DBs since this approach
is not sustainable.
"""

OLD_DB_CREATE_TIMED_BALANCES = """
CREATE TABLE IF NOT EXISTS timed_balances (
    time INTEGER,
    currency VARCHAR[12],
    amount TEXT,
    usd_value TEXT,
    PRIMARY KEY (time, currency)
);
"""

OLD_DB_CREATE_TIMED_LOCATION_DATA = """
CREATE TABLE IF NOT EXISTS timed_location_data (
    time INTEGER,
    location VARCHAR[24],
    usd_value TEXT,
    PRIMARY KEY (time, location)
);
"""

OLD_DB_CREATE_USER_CREDENTIALS = """
CREATE TABLE IF NOT EXISTS user_credentials (
    name VARCHAR[24] NOT NULL PRIMARY KEY,
    api_key TEXT,
    api_secret TEXT
);
"""

OLD_DB_CREATE_BLOCKCHAIN_ACCOUNTS = """
CREATE TABLE IF NOT EXISTS blockchain_accounts (
    blockchain VARCHAR[24],
    account TEXT NOT NULL PRIMARY KEY
);
"""

OLD_DB_CREATE_MULTISETTINGS = """
CREATE TABLE IF NOT EXISTS multisettings (
    name VARCHAR[24] NOT NULL,
    value TEXT,
    UNIQUE(name, value)
);
"""

OLD_DB_CREATE_CURRENT_BALANCES = """
CREATE TABLE IF NOT EXISTS current_balances (
    asset VARCHAR[24] NOT NULL PRIMARY KEY,
    amount TEXT
);
"""

OLD_DB_CREATE_TRADES = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY ASC,
    time INTEGER,
    location VARCHAR[24],
    pair VARCHAR[24],
    type VARCHAR[12],
    amount TEXT,
    rate TEXT,
    fee TEXT,
    fee_currency VARCHAR[10],
    link TEXT,
    notes TEXT
);
"""

OLD_DB_CREATE_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    name VARCHAR[24] NOT NULL PRIMARY KEY,
    value TEXT
);
"""

OLD_DB_SCRIPT_CREATE_TABLES = """
PRAGMA foreign_keys=off;
BEGIN TRANSACTION;
{}{}{}{}{}{}{}{}
COMMIT;
PRAGMA foreign_keys=on;
""".format(
    OLD_DB_CREATE_TIMED_BALANCES,
    OLD_DB_CREATE_TIMED_LOCATION_DATA,
    OLD_DB_CREATE_USER_CREDENTIALS,
    OLD_DB_CREATE_BLOCKCHAIN_ACCOUNTS,
    OLD_DB_CREATE_MULTISETTINGS,
    OLD_DB_CREATE_CURRENT_BALANCES,
    OLD_DB_CREATE_TRADES,
    OLD_DB_CREATE_SETTINGS,
)
