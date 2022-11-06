DB_CREATE_ETHEREUM_TOKENS_LIST = """
CREATE TABLE IF NOT EXISTS underlying_tokens_list (
    identifier TEXT NOT NULL,
    weight TEXT NOT NULL,
    parent_token_entry TEXT NOT NULL,
    FOREIGN KEY(parent_token_entry) REFERENCES evm_tokens(identifier)
        ON DELETE CASCADE ON UPDATE CASCADE
    FOREIGN KEY(identifier) REFERENCES evm_tokens(identifier) ON UPDATE CASCADE ON DELETE CASCADE
    PRIMARY KEY(identifier, parent_token_entry)
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
/* AVALANCHE TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('X', 24);
/* SOLANA TOKEN */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('Y', 25);
/* NFT */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('Z', 26);
/* CUSTOM ASSET */
INSERT OR IGNORE INTO asset_types(type, seq) VALUES ('[', 27);
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

# The common_asset_details contains information common for all the crypto-assets
# leaving to the assets table information that is shared among all the assets.
DB_CREATE_COMMON_ASSET_DETAILS = """
CREATE TABLE IF NOT EXISTS common_asset_details(
    identifier TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
    symbol TEXT,
    coingecko TEXT,
    cryptocompare TEXT,
    forked TEXT,
    started INTEGER,
    swapped_for TEXT,
    FOREIGN KEY(forked) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE SET NULL,
    FOREIGN KEY(identifier) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY(swapped_for) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE SET NULL
);
"""

# For every assets row we have either a row in the common_asset_details table or in the
# custom_assets table. The identifier of the asset is the primary key of the table
# and allows to create the relation with common_asset_details table and the evm_tokens table
# We declare the identifier to be case insensitive .This is so that queries like
# cETH and CETH all work and map to the same asset
DB_CREATE_ASSETS = """
CREATE TABLE IF NOT EXISTS assets (
    identifier TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
    name TEXT,
    type CHAR(1) NOT NULL DEFAULT('A') REFERENCES asset_types(type)
);
"""

DB_CREATE_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    name VARCHAR[24] NOT NULL PRIMARY KEY,
    value TEXT
);
"""

# The evm_tokens table contains information to represent the tokens on every evm chain. It uses
# the asset identifier to reference the asset table allowing for a delete on cascade. Token kind
# and chain are two enum fields where token_kind represent the type of token e.g. ERC20 or ERC721.
# chain is also an enum and it maps to the different chains e.g. ETHEREUM, BINANCE, AVALANCHE...
# Protocol is a text field that we fill with pre selected values in the code and allows to group
# assets by their protocol. All the curve assets are identified by this field and the uniswap pool
# tokens as well. The decimals field is allowed to be NULL since for some tokens is not possible to
# get them or set a value. In the code for tokens that are not NFTs use 18 as default.
DB_CREATE_EVM_TOKENS = """
CREATE TABLE IF NOT EXISTS evm_tokens (
    identifier TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
    token_kind CHAR(1) NOT NULL DEFAULT('A') REFERENCES token_kinds(token_kind),
    chain INTEGER NOT NULL,
    address VARCHAR[42] NOT NULL,
    decimals INTEGER,
    protocol TEXT,
    FOREIGN KEY(identifier) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE
);
"""

# The multiassets_mappings table and asset_collections table work together. This table allows to
# create a relation between the representation of the same asset in different chains. For example
# for USDC we would create a row in asset_collections and then we would create as many entries in
# the multiasset_mappings as USDC tokens we have in our database. This table allows to create a
# relation between all the assets that should be treated as the same.
DB_CREATE_MULTIASSET_MAPPINGS = """
CREATE TABLE IF NOT EXISTS multiasset_mappings(
    collection_id INTEGER NOT NULL,
    asset TEXT NOT NULL,
    FOREIGN KEY(collection_id) REFERENCES asset_collections(id) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE
);
"""  # noqa: E501

# The asset_collections table allows to set common information for related assets as described in
# the multiasset_mappings table. The reason to have a custom name and symbol is that for some
# tokens those properties are not the same across different chains. For example in gnosis chain
# USDC uses USD//C as symbol for the USDC token. This table addresses this problem by creating a
# common name and symbol for those assets allowing a clean representation for the users and
# working as common row to connect all the related assets.
DB_CREATE_ASSET_COLLECTIONS = """
CREATE TABLE IF NOT EXISTS asset_collections(
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    symbol TEXT NOT NULL
);
"""

DB_CREATE_USER_OWNED_ASSETS = """
CREATE TABLE IF NOT EXISTS user_owned_assets (
    asset_id VARCHAR[24] NOT NULL PRIMARY KEY,
    FOREIGN KEY(asset_id) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE
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
/* MANUAL_CURRENT */
INSERT OR IGNORE INTO price_history_source_types(type, seq) VALUES ('E', 5);
/* DEFILLAMA */
INSERT OR IGNORE INTO price_history_source_types(type, seq) VALUES ('F', 6);
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

DB_CREATE_BINANCE_PAIRS = """
CREATE TABLE IF NOT EXISTS binance_pairs (
    pair TEXT NOT NULL,
    base_asset TEXT NOT NULL,
    quote_asset TEXT NOT NULL,
    location TEXT NOT NULL,
    FOREIGN KEY(base_asset) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY(quote_asset) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
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

# Similar to the common_asset_details table this table is used for custom assets that the user
# wants to to track. Also we use the asset identifier to relate this table with the assets table
# allowing a cascade on delete. The notes fields allows for adding relevant information about the
# asset by the user. The type field is a string field that is filled by the user. This allows to
# createsomething like a label so the user can visually see what kind of assets (s)he has. All the
# available types can be queried by selecting with the unique distinct the type column and then
# show them to the user.
# The way to create a custom asset would be:
# 1. Create a row in the assets table with the type custom asset
# 2. Create a row in the custom_assets that references the previously created row
DB_CREATE_CUSTOM_ASSET = """
CREATE TABLE IF NOT EXISTS custom_assets(
    identifier TEXT NOT NULL PRIMARY KEY,
    notes TEXT,
    type TEXT NOT NULL COLLATE NOCASE,
    FOREIGN KEY(identifier) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE
);
"""

DB_CREATE_GENERAL_CACHE = """
CREATE TABLE IF NOT EXISTS general_cache (
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    last_queried_ts INTEGER NOT NULL,
    PRIMARY KEY(key, value)
);
"""

DB_SCRIPT_CREATE_TABLES = f"""
PRAGMA foreign_keys=off;
BEGIN TRANSACTION;
{DB_CREATE_TOKEN_KINDS}
{DB_CREATE_ETHEREUM_TOKENS_LIST}
{DB_CREATE_SETTINGS}
{DB_CREATE_ASSET_TYPES}
{DB_CREATE_ASSETS}
{DB_CREATE_EVM_TOKENS}
{DB_CREATE_MULTIASSET_MAPPINGS}
{DB_CREATE_COMMON_ASSET_DETAILS}
{DB_CREATE_USER_OWNED_ASSETS}
{DB_CREATE_PRICE_HISTORY_SOURCE_TYPES}
{DB_CREATE_PRICE_HISTORY}
{DB_CREATE_BINANCE_PAIRS}
{DB_CREATE_ADDRESS_BOOK}
{DB_CREATE_CUSTOM_ASSET}
{DB_CREATE_ASSET_COLLECTIONS}
{DB_CREATE_GENERAL_CACHE}
COMMIT;
PRAGMA foreign_keys=on;
"""
