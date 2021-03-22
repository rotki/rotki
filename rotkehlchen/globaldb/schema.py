DB_CREATE_ETHEREUM_TOKENS_LIST = """
CREATE TABLE IF NOT EXISTS underlying_tokens_list (
    address VARCHAR[42] NOT NULL,
    weight TEXT NOT NULL,
    parent_token_entry TEXT NOT NULL,
    FOREIGN KEY(parent_token_entry) REFERENCES ethereum_tokens(address) ON DELETE CASCADE
    FOREIGN KEY(address) REFERENCES ethereum_tokens(address)
    PRIMARY KEY(address, parent_token_entry)
);
"""  # noqa: E501

DB_CREATE_ETHEREUM_TOKENS = """
CREATE TABLE IF NOT EXISTS ethereum_tokens (
    address VARCHAR[42] PRIMARY KEY NOT NULL,
    decimals INTEGER,
    name TEXT,
    symbol TEXT,
    started INTEGER,
    swapped_for TEXT,
    coingecko TEXT,
    cryptocompare TEXT,
    protocol TEXT,
    FOREIGN KEY(swapped_for) REFERENCES assets(identifier)
);
"""

# Custom enum table for asset types
DB_CREATE_ASSET_TYPES = """
CREATE TABLE IF NOT EXISTS asset_types (
  type    CHAR(1)       PRIMARY KEY NOT NULL,
  seq     INTEGER UNIQUE
);
/* FIAT */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('A', 1);
/* OWN CHAIN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('B', 2);
/* ETHEREUM TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('C', 3);
/* OMNI TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('D', 4);
/* NEO TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('E', 5);
/* COUNTERPARTY TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('F', 6);
/* BITSHARES TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('G', 7);
/* ARDOR TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('H', 8);
/* NXT TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('I', 9);
/* UBIQ TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('J', 10);
/* NUBITS TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('K', 11);
/* BURST TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('L', 12);
/* WAVES TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('M', 13);
/* QTUM TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('N', 14);
/* STELLAR TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('O', 15);
/* TRON TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('P', 16);
/* ONTOLOGY_TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('Q', 17);
/* VECHAIN TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('R', 18);
/* BINANCE TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('S', 19);
/* EOS TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('T', 20);
/* FUSION TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('U', 21);
/* LUNIVERSE TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('V', 22);
/* OTHER */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('W', 23);
"""

# Using asset_id as a primary key here since nothing else is guaranteed to be unique
# Advantage we have here is that by deleting the parent asset this also gets deleted
DB_CREATE_COMMON_ASSET_DETAILS = """
CREATE TABLE IF NOT EXISTS common_asset_details (
    asset_id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    symbol TEXT,
    started INTEGER,
    forked STRING,
    swapped_for STRING,
    coingecko TEXT,
    cryptocompare TEXT,
    FOREIGN KEY(asset_id) REFERENCES assets(identifier) ON DELETE CASCADE,
    FOREIGN KEY(swapped_for) REFERENCES assets(identifier),
    FOREIGN KEY(forked) REFERENCES assets(identifier)
);
"""

# We declare the identifier to be case insensitive .This is so that queries like
# cETH and CETH all work and map to the same asset
DB_CREATE_ASSETS = """
CREATE TABLE IF NOT EXISTS assets (
    identifier TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
    type CHAR(1) NOT NULL DEFAULT('A') REFERENCES asset_types(type),
    details_reference TEXT
);
"""

DB_CREATE_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    name VARCHAR[24] NOT NULL PRIMARY KEY,
    value TEXT
);
"""

DB_CREATE_USER_OWNED_ASSETS = """
CREATE TABLE IF NOT EXISTS user_owned_assets (
    asset_id VARCHAR[24] NOT NULL PRIMARY KEY,
    FOREIGN KEY(asset_id) REFERENCES assets(identifier)
);
"""

DB_SCRIPT_CREATE_TABLES = """
PRAGMA foreign_keys=off;
BEGIN TRANSACTION;
{}{}{}{}{}{}{}
COMMIT;
PRAGMA foreign_keys=on;
""".format(
    DB_CREATE_ETHEREUM_TOKENS,
    DB_CREATE_ETHEREUM_TOKENS_LIST,
    DB_CREATE_SETTINGS,
    DB_CREATE_ASSET_TYPES,
    DB_CREATE_ASSETS,
    DB_CREATE_COMMON_ASSET_DETAILS,
    DB_CREATE_USER_OWNED_ASSETS,
)
