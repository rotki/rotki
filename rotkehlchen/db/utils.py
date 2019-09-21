from enum import Enum
from typing import List, NamedTuple

from rotkehlchen.assets.asset import Asset
from rotkehlchen.typing import BTCAddress, ChecksumEthAddress, Timestamp

ROTKEHLCHEN_DB_VERSION = 6


class BlockchainAccounts(NamedTuple):
    eth: List[ChecksumEthAddress]
    btc: List[BTCAddress]


class AssetBalance(NamedTuple):
    time: Timestamp
    asset: Asset
    amount: str
    usd_value: str


class SingleAssetBalance(NamedTuple):
    time: Timestamp
    amount: str
    usd_value: str


class LocationData(NamedTuple):
    time: Timestamp
    location: str
    usd_value: str


class DBStartupAction(Enum):
    NOTHING = 1
    UPGRADE_3_4 = 2
    STUCK_4_3 = 3


# Custom enum table for trade types
DB_CREATE_TRADE_TYPE = """
CREATE TABLE IF NOT EXISTS trade_type (
  type    CHAR(1)       PRIMARY KEY NOT NULL,
  seq     INTEGER UNIQUE
);
/* Buy Type*/
INSERT OR IGNORE INTO trade_type(type, seq) VALUES ('A', 1);
/* Sell Type*/
INSERT OR IGNORE INTO trade_type(type, seq) VALUES ('B', 2);
/* Settlement Buy Type*/
INSERT OR IGNORE INTO trade_type(type, seq) VALUES ('C', 3);
/* Settlement Sell Type*/
INSERT OR IGNORE INTO trade_type(type, seq) VALUES ('D', 4);
"""

DB_CREATE_TIMED_BALANCES = """
CREATE TABLE IF NOT EXISTS timed_balances (
    time INTEGER,
    currency VARCHAR[12],
    amount TEXT,
    usd_value TEXT,
    PRIMARY KEY (time, currency)
);
"""

DB_CREATE_TIMED_LOCATION_DATA = """
CREATE TABLE IF NOT EXISTS timed_location_data (
    time INTEGER,
    location VARCHAR[24],
    usd_value TEXT,
    PRIMARY KEY (time, location)
);
"""

DB_CREATE_USER_CREDENTIALS = """
CREATE TABLE IF NOT EXISTS user_credentials (
    name VARCHAR[24] NOT NULL PRIMARY KEY,
    api_key TEXT,
    api_secret TEXT
);
"""

DB_CREATE_BLOCKCHAIN_ACCOUNTS = """
CREATE TABLE IF NOT EXISTS blockchain_accounts (
    blockchain VARCHAR[24],
    account TEXT NOT NULL PRIMARY KEY
);
"""

DB_CREATE_MULTISETTINGS = """
CREATE TABLE IF NOT EXISTS multisettings (
    name VARCHAR[24] NOT NULL,
    value TEXT,
    UNIQUE(name, value)
);
"""

DB_CREATE_CURRENT_BALANCES = """
CREATE TABLE IF NOT EXISTS current_balances (
    asset VARCHAR[24] NOT NULL PRIMARY KEY,
    amount TEXT
);
"""

DB_CREATE_TRADES = """
CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    time INTEGER,
    location VARCHAR[24],
    pair VARCHAR[24],
    type CHAR(1) NOT NULL DEFAULT ('B') REFERENCES trade_type(type),
    amount TEXT,
    rate TEXT,
    fee TEXT,
    fee_currency VARCHAR[10],
    link TEXT,
    notes TEXT
);
"""

DB_CREATE_MARGIN = """
CREATE TABLE IF NOT EXISTS margin_positions (
    id TEXT PRIMARY KEY,
    location VARCHAR[24],
    open_time INTEGER,
    close_time INTEGER,
    profit_loss TEXT,
    pl_currency VARCHAR[10],
    fee TEXT,
    fee_currency VARCHAR[10],
    link TEXT,
    notes TEXT
);
"""

DB_CREATE_ASSET_MOVEMENTS = """
CREATE TABLE IF NOT EXISTS asset_movements (
    id TEXT PRIMARY KEY,
    location VARCHAR[24],
    category VARCHAR[16],
    time INTEGER,
    asset VARCHAR[10],
    amount TEXT,
    fee_asset VARCHAR[10],
    fee TEXT,
    link TEXT
);
"""

DB_CREATE_LAST_TIMESTAMPS = """
CREATE TABLE IF NOT EXISTS last_timestamps (
    name VARCHAR[24] NOT NULL PRIMARY KEY,
    value INTEGER
);
"""

DB_CREATE_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    name VARCHAR[24] NOT NULL PRIMARY KEY,
    value TEXT
);
"""

DB_SCRIPT_REIMPORT_DATA = """
PRAGMA foreign_keys=off;
BEGIN TRANSACTION;

ALTER TABLE timed_balances RENAME TO _timed_balances;

{}

INSERT INTO timed_balances (time, currency, amount, usd_value)
SELECT time, currency, amount, usd_value FROM _timed_balances;
DROP TABLE _timed_balances;


ALTER TABLE timed_location_data RENAME TO _timed_location_data;

{}

INSERT INTO timed_location_data (time, location, usd_value)
SELECT time, location, usd_value FROM _timed_location_data;
DROP TABLE _timed_location_data;


ALTER TABLE user_credentials RENAME TO _user_credentials;

{}

INSERT INTO user_credentials (name, api_key, api_secret)
SELECT name, api_key, api_secret FROM _user_credentials;
DROP TABLE _user_credentials;


ALTER TABLE blockchain_accounts RENAME TO _blockchain_accounts;

{}

INSERT INTO blockchain_accounts (blockchain, account)
SELECT blockchain, account FROM _blockchain_accounts;
DROP TABLE _blockchain_accounts;


ALTER TABLE multisettings RENAME TO _multisettings;

{}

INSERT INTO multisettings (name, value)
SELECT name, value FROM _multisettings;
DROP TABLE _multisettings;


ALTER TABLE current_balances RENAME TO _current_balances;

{}

INSERT INTO current_balances (asset, amount)
SELECT asset, amount FROM _current_balances;
DROP TABLE _current_balances;


ALTER TABLE trades RENAME TO _trades;

{}

INSERT INTO trades (id, time, location, pair, type, amount, rate, fee, fee_currency, link, notes)
SELECT id, time, location, pair, type, amount, rate, fee, fee_currency, link, notes FROM _trades;
DROP TABLE _trades;

ALTER TABLE settings RENAME TO _settings;

{}

INSERT INTO settings (name, value)
SELECT name, value FROM _settings;
DROP TABLE _settings;


COMMIT;
PRAGMA foreign_keys=on;
""".format(
    DB_CREATE_TIMED_BALANCES,
    DB_CREATE_TIMED_LOCATION_DATA,
    DB_CREATE_USER_CREDENTIALS,
    DB_CREATE_BLOCKCHAIN_ACCOUNTS,
    DB_CREATE_MULTISETTINGS,
    DB_CREATE_CURRENT_BALANCES,
    DB_CREATE_TRADES,
    DB_CREATE_SETTINGS,
)

DB_SCRIPT_CREATE_TABLES = """
PRAGMA foreign_keys=off;
BEGIN TRANSACTION;
{}{}{}{}{}{}{}{}{}{}{}{}
COMMIT;
PRAGMA foreign_keys=on;
""".format(
    DB_CREATE_TRADE_TYPE,
    DB_CREATE_TIMED_BALANCES,
    DB_CREATE_TIMED_LOCATION_DATA,
    DB_CREATE_USER_CREDENTIALS,
    DB_CREATE_BLOCKCHAIN_ACCOUNTS,
    DB_CREATE_MULTISETTINGS,
    DB_CREATE_CURRENT_BALANCES,
    DB_CREATE_TRADES,
    DB_CREATE_MARGIN,
    DB_CREATE_ASSET_MOVEMENTS,
    DB_CREATE_LAST_TIMESTAMPS,
    DB_CREATE_SETTINGS,
)
