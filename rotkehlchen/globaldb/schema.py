DB_CREATE_ETHEREUM_TOKENS_LIST = """
CREATE TABLE IF NOT EXISTS underlying_tokens_list (
    identifier TEXT NOT NULL,
    weight TEXT NOT NULL,
    parent_token_entry TEXT NOT NULL,
    FOREIGN KEY(parent_token_entry) REFERENCES evm_tokens(identifier)
        ON DELETE CASCADE ON UPDATE CASCADE
    FOREIGN KEY(identifier) REFERENCES evm_tokens(identifier) ON UPDATE CASCADE
    PRIMARY KEY(identifier, parent_token_entry)
);
"""  # noqa: E501

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
/* AVALANCHE TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('X', 24);
/* SOLANA TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('Y', 25);
/* NFT */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('Z', 26);
"""

# Custom enum table for chains
DB_CREATE_CHAIN_IDS = """
CREATE TABLE IF NOT EXISTS chain_ids (
  chain    CHAR(1)       PRIMARY KEY NOT NULL,
  seq     INTEGER UNIQUE
);
/* ETHEREUM */
INSERT OR IGNORE INTO chain_ids(chain, seq) VALUES ('A', 1);
/* OPTIMISM */
INSERT OR IGNORE INTO chain_ids(chain, seq) VALUES ('B', 2);
/* BINANCE */
INSERT OR IGNORE INTO chain_ids(chain, seq) VALUES ('C', 3);
/* GNOSIS */
INSERT OR IGNORE INTO chain_ids(chain, seq) VALUES ('D', 4);
/* MATIC */
INSERT OR IGNORE INTO chain_ids(chain, seq) VALUES ('E', 5);
/* FANTOM */
INSERT OR IGNORE INTO chain_ids(chain, seq) VALUES ('F', 6);
/* ARBITRUM */
INSERT OR IGNORE INTO chain_ids(chain, seq) VALUES ('G', 7);
/* AVALANCHE */
INSERT OR IGNORE INTO chain_ids(chain, seq) VALUES ('H', 8);
"""

# Custom enum table for token kindss
DB_CREATE_TOKEN_KINDS = """
CREATE TABLE IF NOT EXISTS token_kinds (
  token_kind    CHAR(1)       PRIMARY KEY NOT NULL,
  seq     INTEGER UNIQUE
);
/* ERC20 */
INSERT OR IGNORE INTO token_kinds(token_kind, seq) VALUES ('A', 1);
/* ERC721 */
INSERT OR IGNORE INTO token_kinds(token_kind, seq) VALUES ('B', 2);
/* UNKNOWN */
INSERT OR IGNORE INTO token_kinds(token_kind, seq) VALUES ('C', 3);
"""

# Using asset_id as a primary key here since nothing else is guaranteed to be unique
# Advantage we have here is that by deleting the parent asset this also gets deleted
DB_CREATE_COMMON_ASSET_DETAILS = """
CREATE TABLE IF NOT EXISTS common_asset_details(
    identifier TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
    name TEXT,
    symbol TEXT,
    coingecko TEXT,
    cryptocompare TEXT,
    forked TEXT,
    FOREIGN KEY(forked) REFERENCES assets(identifier) ON UPDATE CASCADE
);
"""

# We declare the identifier to be case insensitive .This is so that queries like
# cETH and CETH all work and map to the same asset
# details_reference is not a FOREIGN key here since it can be for multiple tables
DB_CREATE_ASSETS = """
CREATE TABLE IF NOT EXISTS assets (
    identifier TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
    type CHAR(1) NOT NULL DEFAULT('A') REFERENCES asset_types(type),
    started INTEGER,
    swapped_for TEXT,
    FOREIGN KEY(swapped_for) REFERENCES assets(identifier) ON UPDATE CASCADE
);
"""

DB_CREATE_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    name VARCHAR[24] NOT NULL PRIMARY KEY,
    value TEXT
);
"""

DB_CREATE_EVM_TOKENS = """
CREATE TABLE IF NOT EXISTS evm_tokens (
    identifier TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
    token_kind CHAR(1) NOT NULL DEFAULT('A') REFERENCES token_kinds(token_kind),
    chain CHAR(1) NOT NULL DEFAULT('A') REFERENCES chain_ids(chain),
    address VARCHAR[42] NOT NULL,
    decimals INTEGER,
    protocol TEXT
);
"""

DB_CREATE_MULTIASSETS = """
CREATE TABLE IF NOT EXISTS multiasset_collector(
    identifier TEXT NOT NULL,
    child_asset_id TEXT,
    FOREIGN KEY(child_asset_id) REFERENCES assets(identifier) ON UPDATE CASCADE
    FOREIGN KEY(identifier) REFERENCES assets(identifier) ON UPDATE CASCADE
    PRIMARY KEY(identifier, child_asset_id)
);
"""

DB_CREATE_USER_OWNED_ASSETS = """
CREATE TABLE IF NOT EXISTS user_owned_assets (
    asset_id VARCHAR[24] NOT NULL PRIMARY KEY,
    FOREIGN KEY(asset_id) REFERENCES assets(identifier) ON UPDATE CASCADE
);
"""

# Custom enum table for price history source
DB_CREATE_PRICE_HISTORY_SOURCE_TYPES = """
CREATE TABLE IF NOT EXISTS price_history_source_types (
  type    CHAR(1)       PRIMARY KEY NOT NULL,
  seq     INTEGER UNIQUE
);
/* MANUAL */
INSERT OR IGNORE INTO price_history_source_types(type, seq) VALUES ('A', 1);
/* COINGECKO */
INSERT OR IGNORE INTO price_history_source_types(type, seq) VALUES ('B', 2);
/* CRYPTOCOMPARE */
INSERT OR IGNORE INTO price_history_source_types(type, seq) VALUES ('C', 3);
/* XRATESCOM */
INSERT OR IGNORE INTO price_history_source_types(type, seq) VALUES ('D', 4);
"""

DB_CREATE_PRICE_HISTORY = """
CREATE TABLE IF NOT EXISTS price_history (
    from_asset TEXT NOT NULL COLLATE NOCASE,
    to_asset TEXT NOT NULL COLLATE NOCASE,
    source_type CHAR(1) NOT NULL DEFAULT('A') REFERENCES price_history_source_types(type),
    timestamp INTEGER NOT NULL,
    price TEXT NOT NULL,
    FOREIGN KEY(from_asset) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY(to_asset) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY(from_asset, to_asset, source_type, timestamp)
);
"""

DB_CREATE_BINANCE_PARIS = """
CREATE TABLE IF NOT EXISTS binance_pairs (
    pair TEXT NOT NULL,
    base_asset TEXT NOT NULL,
    quote_asset TEXT NOT NULL,
    location TEXT NOT NULL,
    FOREIGN KEY(base_asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
    FOREIGN KEY(quote_asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
    PRIMARY KEY(pair, location)
);
"""

DB_CREATE_ADDRESS_BOOK = """
CREATE TABLE IF NOT EXISTS address_book (
    address TEXT NOT NULL,
    blockchain TEXT NOT NULL DEFAULT "ETH",
    name TEXT NOT NULL,
    PRIMARY KEY(address, blockchain)
);
"""

DB_CREATE_CUSTOM_ASSET = """
CREATE TABLE IF NOT EXISTS custom_asset(
    identifier INTEGER NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    symbol TEXT,
    notes TEXT,
    asset_type TEXT
);
"""

DB_CREATE_ASSET_COLLECTION_PROPERTIES = """
CREATE TABLE IF NOT EXISTS asset_collection_properties(
    identifier TEXT NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    FOREIGN KEY(identifier) REFERENCES multiasset_collector(identifier) ON UPDATE CASCADE ON DELETE CASCADE
);
"""  # noqa: E501

DB_SCRIPT_CREATE_TABLES = f"""
PRAGMA foreign_keys=off;
BEGIN TRANSACTION;
{DB_CREATE_CHAIN_IDS}
{DB_CREATE_TOKEN_KINDS}
{DB_CREATE_ETHEREUM_TOKENS_LIST}
{DB_CREATE_SETTINGS}
{DB_CREATE_ASSET_TYPES}
{DB_CREATE_ASSETS}
{DB_CREATE_EVM_TOKENS}
{DB_CREATE_MULTIASSETS}
{DB_CREATE_COMMON_ASSET_DETAILS}
{DB_CREATE_USER_OWNED_ASSETS}
{DB_CREATE_PRICE_HISTORY_SOURCE_TYPES}
{DB_CREATE_PRICE_HISTORY}
{DB_CREATE_BINANCE_PARIS}
{DB_CREATE_ADDRESS_BOOK}
{DB_CREATE_CUSTOM_ASSET}
{DB_CREATE_ASSET_COLLECTION_PROPERTIES}
COMMIT;
PRAGMA foreign_keys=on;
"""
