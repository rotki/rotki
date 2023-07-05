# Custom enum table for trade types
DB_CREATE_TRADE_TYPE = """
CREATE TABLE IF NOT EXISTS trade_type (
  type    CHAR(1)       PRIMARY KEY NOT NULL,
  seq     INTEGER UNIQUE
);
/* Buy Type */
INSERT OR IGNORE INTO trade_type(type, seq) VALUES ('A', 1);
/* Sell Type */
INSERT OR IGNORE INTO trade_type(type, seq) VALUES ('B', 2);
/* Settlement Buy Type */
INSERT OR IGNORE INTO trade_type(type, seq) VALUES ('C', 3);
/* Settlement Sell Type */
INSERT OR IGNORE INTO trade_type(type, seq) VALUES ('D', 4);
"""

# Custom enum table for locations
DB_CREATE_LOCATION = """
CREATE TABLE IF NOT EXISTS location (
  location    CHAR(1)       PRIMARY KEY NOT NULL,
  seq     INTEGER UNIQUE
);
/* External */
INSERT OR IGNORE INTO location(location, seq) VALUES ('A', 1);
/* Kraken */
INSERT OR IGNORE INTO location(location, seq) VALUES ('B', 2);
/* Poloniex */
INSERT OR IGNORE INTO location(location, seq) VALUES ('C', 3);
/* Bittrex */
INSERT OR IGNORE INTO location(location, seq) VALUES ('D', 4);
/* Binance */
INSERT OR IGNORE INTO location(location, seq) VALUES ('E', 5);
/* Bitmex */
INSERT OR IGNORE INTO location(location, seq) VALUES ('F', 6);
/* Coinbase */
INSERT OR IGNORE INTO location(location, seq) VALUES ('G', 7);
/* Total */
INSERT OR IGNORE INTO location(location, seq) VALUES ('H', 8);
/* Banks */
INSERT OR IGNORE INTO location(location, seq) VALUES ('I', 9);
/* Blockchain */
INSERT OR IGNORE INTO location(location, seq) VALUES ('J', 10);
/* Coinbase Pro */
INSERT OR IGNORE INTO location(location, seq) VALUES ('K', 11);
/* Gemini */
INSERT OR IGNORE INTO location(location, seq) VALUES ('L', 12);
/* Equities */
INSERT OR IGNORE INTO location(location, seq) VALUES ('M', 13);
/* Real estate */
INSERT OR IGNORE INTO location(location, seq) VALUES ('N', 14);
/* Commodities */
INSERT OR IGNORE INTO location(location, seq) VALUES ('O', 15);
/* Crypto.com */
INSERT OR IGNORE INTO location(location, seq) VALUES ('P', 16);
/* Uniswap */
INSERT OR IGNORE INTO location(location, seq) VALUES ('Q', 17);
/* Bitstamp */
INSERT OR IGNORE INTO location(location, seq) VALUES ('R', 18);
/* Binance US */
INSERT OR IGNORE INTO location(location, seq) VALUES ('S', 19);
/* Bitfinex */
INSERT OR IGNORE INTO location(location, seq) VALUES ('T', 20);
/* Bitcoin.de */
INSERT OR IGNORE INTO location(location, seq) VALUES ('U', 21);
/* ICONOMI */
INSERT OR IGNORE INTO location(location, seq) VALUES ('V', 22);
/* KUCOIN */
INSERT OR IGNORE INTO location(location, seq) VALUES ('W', 23);
/* BALANCER */
INSERT OR IGNORE INTO location(location, seq) VALUES ('X', 24);
/* LOOPRING */
INSERT OR IGNORE INTO location(location, seq) VALUES ('Y', 25);
/* FTX */
INSERT OR IGNORE INTO location(location, seq) VALUES ('Z', 26);
/* NEXO */
INSERT OR IGNORE INTO location(location, seq) VALUES ('[', 27);
/* BlockFI */
INSERT OR IGNORE INTO location(location, seq) VALUES ('\\', 28);
/* IndependentReserve */
INSERT OR IGNORE INTO location(location, seq) VALUES (']', 29);
/* Gitcoin */
INSERT OR IGNORE INTO location(location, seq) VALUES ('^', 30);
/* Sushiswap */
INSERT OR IGNORE INTO location(location, seq) VALUES ('_', 31);
/* ShapeShift */
INSERT OR IGNORE INTO location(location, seq) VALUES ('`', 32);
/* Uphold */
INSERT OR IGNORE INTO location(location, seq) VALUES ('a', 33);
/* Bitpanda */
INSERT OR IGNORE INTO location(location, seq) VALUES ('b', 34);
/* Bisq */
INSERT OR IGNORE INTO location(location, seq) VALUES ('c', 35);
/* FTX US */
INSERT OR IGNORE INTO location(location, seq) VALUES ('d', 36);
/* OKX */
INSERT OR IGNORE INTO location(location, seq) VALUES ('e', 37);
/* ETHEREUM */
INSERT OR IGNORE INTO location(location, seq) VALUES ('f', 38);
/* OPTIMISM */
INSERT OR IGNORE INTO location(location, seq) VALUES ('g', 39);
/* POLYGON_POS */
INSERT OR IGNORE INTO location(location, seq) VALUES ('h', 40);
"""

# Custom enum table for AssetMovement categories (deposit/withdrawal)
DB_CREATE_ASSET_MOVEMENT_CATEGORY = """
CREATE TABLE IF NOT EXISTS asset_movement_category (
  category    CHAR(1)       PRIMARY KEY NOT NULL,
  seq     INTEGER UNIQUE
);
/* Deposit Category */
INSERT OR IGNORE INTO asset_movement_category(category, seq) VALUES ('A', 1);
/* Withdrawal Category */
INSERT OR IGNORE INTO asset_movement_category(category, seq) VALUES ('B', 2);
"""

# Custom enum table for Balance categories (asset/liability)
DB_CREATE_BALANCE_CATEGORY = """
CREATE TABLE IF NOT EXISTS balance_category (
  category    CHAR(1)       PRIMARY KEY NOT NULL,
  seq     INTEGER UNIQUE
);
/* Asset Category */
INSERT OR IGNORE INTO balance_category(category, seq) VALUES ('A', 1);
/* Liability Category */
INSERT OR IGNORE INTO balance_category(category, seq) VALUES ('B', 2);
"""

# Custom enum table for LedgerAction categories (income, expense, loss and more)
DB_CREATE_LEDGER_ACTION_TYPE = """
CREATE TABLE IF NOT EXISTS ledger_action_type (
  type    CHAR(1)       PRIMARY KEY NOT NULL,
  seq     INTEGER UNIQUE
);
/* Income Action Type */
INSERT OR IGNORE INTO ledger_action_type(type, seq) VALUES ('A', 1);
/* Expense Action Type */
INSERT OR IGNORE INTO ledger_action_type(type, seq) VALUES ('B', 2);
/* Loss Action Type */
INSERT OR IGNORE INTO ledger_action_type(type, seq) VALUES ('C', 3);
/* Dividends Income Action Type */
INSERT OR IGNORE INTO ledger_action_type(type, seq) VALUES ('D', 4);
/* Donation Received Action Type */
INSERT OR IGNORE INTO ledger_action_type(type, seq) VALUES ('E', 5);
/* Airdrop Action Type */
INSERT OR IGNORE INTO ledger_action_type(type, seq) VALUES ('F', 6);
/* Gift Action Type */
INSERT OR IGNORE INTO ledger_action_type(type, seq) VALUES ('G', 7);
/* Grant Action Type */
INSERT OR IGNORE INTO ledger_action_type(type, seq) VALUES ('H', 8);
"""

# Custom enum table for taxable action types
DB_CREATE_ACTION_TYPE = """
CREATE TABLE IF NOT EXISTS action_type (
  type    CHAR(1)       PRIMARY KEY NOT NULL,
  seq     INTEGER UNIQUE
);
/* Trade Type */
INSERT OR IGNORE INTO action_type(type, seq) VALUES ('A', 1);
/* Asset Movement Type */
INSERT OR IGNORE INTO action_type(type, seq) VALUES ('B', 2);
/* Ethereum Transaction Type */
INSERT OR IGNORE INTO action_type(type, seq) VALUES ('C', 3);
/* Ledger Actions Type */
INSERT OR IGNORE INTO action_type(type, seq) VALUES ('D', 4);
"""

DB_CREATE_ASSETS = """
CREATE TABLE IF NOT EXISTS assets (
    identifier TEXT NOT NULL PRIMARY KEY
);
"""

DB_CREATE_IGNORED_ACTIONS = """
CREATE TABLE IF NOT EXISTS ignored_actions (
    type CHAR(1) NOT NULL DEFAULT('A') REFERENCES action_type(type),
    identifier TEXT,
    PRIMARY KEY (type, identifier)
);
"""

DB_CREATE_TIMED_BALANCES = """
CREATE TABLE IF NOT EXISTS timed_balances (
    category CHAR(1) NOT NULL DEFAULT('A') REFERENCES balance_category(category),
    timestamp INTEGER,
    currency TEXT,
    amount TEXT,
    usd_value TEXT,
    FOREIGN KEY(currency) REFERENCES assets(identifier) ON UPDATE CASCADE,
    PRIMARY KEY (timestamp, currency, category)
);
"""

DB_CREATE_TIMED_LOCATION_DATA = """
CREATE TABLE IF NOT EXISTS timed_location_data (
    timestamp INTEGER,
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    usd_value TEXT,
    PRIMARY KEY (timestamp, location)
);
"""

DB_CREATE_USER_CREDENTIALS = """
CREATE TABLE IF NOT EXISTS user_credentials (
    name TEXT NOT NULL,
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    api_key TEXT,
    api_secret TEXT,
    passphrase TEXT,
    PRIMARY KEY (name, location)
);
"""

DB_CREATE_USER_CREDENTIALS_MAPPINGS = """
CREATE TABLE IF NOT EXISTS user_credentials_mappings (
    credential_name TEXT NOT NULL,
    credential_location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    setting_name TEXT NOT NULL,
    setting_value TEXT NOT NULL,
    FOREIGN KEY(credential_name, credential_location) REFERENCES user_credentials(name, location) ON DELETE CASCADE ON UPDATE CASCADE,
    PRIMARY KEY (credential_name, credential_location, setting_name)
);
"""  # noqa: E501


DB_CREATE_YEARN_VAULT_EVENTS = """
CREATE TABLE IF NOT EXISTS yearn_vaults_events (
    address VARCHAR[42] NOT NULL,
    event_type VARCHAR[10] NOT NULL,
    from_asset TEXT NOT NULL,
    from_amount TEXT NOT NULL,
    from_usd_value TEXT NOT NULL,
    to_asset TEXT NOT NULL,
    to_amount TEXT NOT NULL,
    to_usd_value TEXT NOT NULL,
    pnl_amount TEXT,
    pnl_usd_value TEXT,
    block_number INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    tx_hash BLOB NOT NULL,
    log_index INTEGER NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY(from_asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
    FOREIGN KEY(to_asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
    PRIMARY KEY (event_type, tx_hash, log_index)
);
"""

DB_CREATE_EXTERNAL_SERVICE_CREDENTIALS = """
CREATE TABLE IF NOT EXISTS external_service_credentials (
    name VARCHAR[30] NOT NULL PRIMARY KEY,
    api_key TEXT
);
"""

DB_CREATE_TAGS_TABLE = """
CREATE TABLE IF NOT EXISTS tags (
    name TEXT NOT NULL PRIMARY KEY COLLATE NOCASE,
    description TEXT,
    background_color TEXT,
    foreground_color TEXT
);
"""

DB_CREATE_BLOCKCHAIN_ACCOUNTS = """
CREATE TABLE IF NOT EXISTS blockchain_accounts (
    blockchain VARCHAR[24] NOT NULL,
    account TEXT NOT NULL,
    label TEXT,
    PRIMARY KEY (blockchain, account)
);
"""

DB_CREATE_XPUBS = """
CREATE TABLE IF NOT EXISTS xpubs (
    xpub TEXT NOT NULL,
    derivation_path TEXT NOT NULL,
    label TEXT,
    blockchain TEXT NOT NULL,
    PRIMARY KEY (xpub, derivation_path, blockchain)
);
"""

DB_CREATE_XPUB_MAPPINGS = """
CREATE TABLE IF NOT EXISTS xpub_mappings (
    address TEXT NOT NULL,
    xpub TEXT NOT NULL,
    derivation_path TEXT NOT NULL,
    account_index INTEGER,
    derived_index INTEGER,
    blockchain TEXT NOT NULL,
    FOREIGN KEY(blockchain, address)
    REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE
    FOREIGN KEY(xpub, derivation_path, blockchain) REFERENCES xpubs(
        xpub,
        derivation_path,
        blockchain
    ) ON DELETE CASCADE
    PRIMARY KEY (address, xpub, derivation_path, blockchain)
);
"""


# Store information about the tokens queried for each combination of account and blockchain.
# The table is designed to have a key-value structure where we use the key `token` to
# identify the tokens queried per address and the key `last_queried_timestamp` to
# determine when the last query was executed
DB_CREATE_EVM_ACCOUNTS_DETAILS = """
CREATE TABLE IF NOT EXISTS evm_accounts_details (
    account VARCHAR[42] NOT NULL,
    chain_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (account, chain_id, key, value)
);
"""

DB_CREATE_MANUALLY_TRACKED_BALANCES = """
CREATE TABLE IF NOT EXISTS manually_tracked_balances (
    id INTEGER PRIMARY KEY,
    asset TEXT NOT NULL,
    label TEXT NOT NULL,
    amount TEXT,
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    category CHAR(1) NOT NULL DEFAULT('A') REFERENCES balance_category(category),
    FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE
);
"""

# Not putting object_reference as a foreign key since multiple objects, not only
# blockchain accounts can have tag mappings (future-proof thinking here)
DB_CREATE_TAG_MAPPINGS = """
CREATE TABLE IF NOT EXISTS tag_mappings (
    object_reference TEXT,
    tag_name TEXT,
    FOREIGN KEY(tag_name) REFERENCES tags(name)
    PRIMARY KEY (object_reference, tag_name)
);
"""

DB_CREATE_MULTISETTINGS = """
CREATE TABLE IF NOT EXISTS multisettings (
    name VARCHAR[24] NOT NULL,
    value TEXT,
    UNIQUE(name, value)
);
"""

DB_CREATE_TRADES = """
CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY NOT NULL,
    timestamp INTEGER NOT NULL,
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    base_asset TEXT NOT NULL,
    quote_asset TEXT NOT NULL,
    type CHAR(1) NOT NULL DEFAULT ('A') REFERENCES trade_type(type),
    amount TEXT NOT NULL,
    rate TEXT NOT NULL,
    fee TEXT,
    fee_currency TEXT,
    link TEXT,
    notes TEXT,
    FOREIGN KEY(base_asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
    FOREIGN KEY(quote_asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
    FOREIGN KEY(fee_currency) REFERENCES assets(identifier) ON UPDATE CASCADE
);
"""

DB_CREATE_MARGIN = """
CREATE TABLE IF NOT EXISTS margin_positions (
    id TEXT PRIMARY KEY,
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    open_time INTEGER,
    close_time INTEGER,
    profit_loss TEXT,
    pl_currency TEXT NOT NULL,
    fee TEXT,
    fee_currency TEXT,
    link TEXT,
    notes TEXT,
    FOREIGN KEY(pl_currency) REFERENCES assets(identifier) ON UPDATE CASCADE,
    FOREIGN KEY(fee_currency) REFERENCES assets(identifier) ON UPDATE CASCADE
);
"""

DB_CREATE_ASSET_MOVEMENTS = """
CREATE TABLE IF NOT EXISTS asset_movements (
    id TEXT PRIMARY KEY,
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    category CHAR(1) NOT NULL DEFAULT('A') REFERENCES asset_movement_category(category),
    address TEXT,
    transaction_id TEXT,
    timestamp INTEGER,
    asset TEXT NOT NULL,
    amount TEXT,
    fee_asset TEXT,
    fee TEXT,
    link TEXT,
    FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
    FOREIGN KEY(fee_asset) REFERENCES assets(identifier) ON UPDATE CASCADE
);
"""

DB_CREATE_LEDGER_ACTIONS = """
CREATE TABLE IF NOT EXISTS ledger_actions (
    identifier INTEGER NOT NULL PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    type CHAR(1) NOT NULL DEFAULT('A') REFERENCES ledger_action_type(type),
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    amount TEXT NOT NULL,
    asset TEXT NOT NULL,
    rate TEXT,
    rate_asset TEXT,
    link TEXT,
    notes TEXT,
    FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
    FOREIGN KEY(rate_asset) REFERENCES assets(identifier) ON UPDATE CASCADE
);
"""

DB_CREATE_EVM_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS evm_transactions (
    identifier INTEGER NOT NULL PRIMARY KEY,
    tx_hash BLOB NOT NULL,
    chain_id INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    block_number INTEGER NOT NULL,
    from_address TEXT NOT NULL,
    to_address TEXT,
    value TEXT NOT NULL,
    gas TEXT NOT NULL,
    gas_price TEXT NOT NULL,
    gas_used TEXT NOT NULL,
    input_data BLOB NOT NULL,
    nonce INTEGER NOT NULL,
    UNIQUE(tx_hash, chain_id)
);
"""

DB_CREATE_OPTIMISM_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS optimism_transactions (
    tx_hash BLOB NOT NULL,
    chain_id INTEGER GENERATED ALWAYS AS (10) VIRTUAL,
    l1_fee TEXT,
    PRIMARY KEY(tx_hash),
    FOREIGN KEY(tx_hash, chain_id) REFERENCES evm_transactions(tx_hash, chain_id) ON DELETE CASCADE ON UPDATE CASCADE
);
"""  # noqa: E501

# from/to address/value is also in the primary key of the internal transactions since
# trace_id, which is returned by etherscan does not guarantee uniqueness. Example:
# https://api.etherscan.io/api?module=account&action=txlistinternal&sort=asc&startBlock=16779092&endBlock=16779092
DB_CREATE_EVM_INTERNAL_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS evm_internal_transactions (
    parent_tx INTEGER NOT NULL,
    trace_id INTEGER NOT NULL,
    from_address TEXT NOT NULL,
    to_address TEXT,
    value TEXT NOT NULL,
    FOREIGN KEY(parent_tx) REFERENCES evm_transactions(identifier) ON DELETE CASCADE ON UPDATE CASCADE,
    PRIMARY KEY(parent_tx, trace_id, from_address, to_address, value)
);
"""  # noqa: E501

DB_CREATE_EVMTX_RECEIPTS = """
CREATE TABLE IF NOT EXISTS evmtx_receipts (
    tx_id INTEGER NOT NULL PRIMARY KEY,
    contract_address TEXT, /* can be null */
    status INTEGER NOT NULL CHECK (status IN (0, 1)),
    type INTEGER NOT NULL,
    FOREIGN KEY(tx_id) REFERENCES evm_transactions(identifier) ON DELETE CASCADE ON UPDATE CASCADE
);
"""

DB_CREATE_EVMTX_RECEIPT_LOGS = """
CREATE TABLE IF NOT EXISTS evmtx_receipt_logs (
    identifier INTEGER NOT NULL PRIMARY KEY,  /* adding identifier here instead of composite key in order to not duplicate in topics which are A LOT */
    tx_id INTEGER NOT NULL,
    log_index INTEGER NOT NULL,
    data BLOB NOT NULL,
    address TEXT NOT NULL,
    removed INTEGER NOT NULL CHECK (removed IN (0, 1)),
    FOREIGN KEY(tx_id) REFERENCES evmtx_receipts(tx_id) ON DELETE CASCADE ON UPDATE CASCADE,
    UNIQUE(tx_id, log_index)
);
"""  # noqa: E501

DB_CREATE_EVMTX_RECEIPT_LOG_TOPICS = """
CREATE TABLE IF NOT EXISTS evmtx_receipt_log_topics (
    log INTEGER NOT NULL,
    topic BLOB NOT NULL,
    topic_index INTEGER NOT NULL,
    FOREIGN KEY(log) REFERENCES evmtx_receipt_logs(identifier) ON DELETE CASCADE ON UPDATE CASCADE,
    PRIMARY KEY(log, topic_index)
);
"""

# TODO: This here shows a weakness of using both chain_id and blockchain to identify
# the chain. May need to change the schema somehow to either use the string identifier
# everywhere as the common denominator. Or perhaps it's also good like this if this is
# the only "bridge" table where both chain_id and blockchain exist for mapping.
DB_CREATE_EVMTX_ADDRESS_MAPPINGS = """
CREATE TABLE IF NOT EXISTS evmtx_address_mappings (
    address TEXT NOT NULL,
    tx_hash BLOB NOT NULL,
    chain_id INTEGER NOT NULL,
    blockchain TEXT NOT NULL,
    FOREIGN KEY(blockchain, address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE,
    FOREIGN KEY(tx_hash, chain_id) references evm_transactions(tx_hash, chain_id) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (address, tx_hash, chain_id)
);
"""  # noqa: E501

DB_CREATE_USED_QUERY_RANGES = """
CREATE TABLE IF NOT EXISTS used_query_ranges (
    name VARCHAR[24] NOT NULL PRIMARY KEY,
    start_ts INTEGER,
    end_ts INTEGER
);
"""

# Currently this table is used only to store a flag that shows whether a transaction is decoded.
DB_CREATE_EVM_TX_MAPPINGS = """
CREATE TABLE IF NOT EXISTS evm_tx_mappings (
    tx_hash BLOB NOT NULL,
    chain_id INTEGER NOT NULL,
    value INTEGER NOT NULL,
    FOREIGN KEY(tx_hash, chain_id) references evm_transactions(tx_hash, chain_id) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (tx_hash, chain_id, value)
);
"""  # noqa: E501

DB_CREATE_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    name VARCHAR[24] NOT NULL PRIMARY KEY,
    value TEXT
);
"""

DB_CREATE_ETH2_VALIDATORS = """
CREATE TABLE IF NOT EXISTS eth2_validators (
    validator_index INTEGER NOT NULL PRIMARY KEY,
    public_key TEXT NOT NULL UNIQUE,
    ownership_proportion TEXT NOT NULL
);
"""

DB_CREATE_ETH2_DAILY_STAKING_DETAILS = """
CREATE TABLE IF NOT EXISTS eth2_daily_staking_details (
    validator_index INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    pnl TEXT NOT NULL,
    FOREIGN KEY(validator_index) REFERENCES eth2_validators(validator_index) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (validator_index, timestamp)
);
"""  # noqa: E501

DB_CREATE_HISTORY_EVENTS = """
CREATE TABLE IF NOT EXISTS history_events (
    identifier INTEGER NOT NULL PRIMARY KEY,
    entry_type INTEGER NOT NULL,
    event_identifier TEXT NOT NULL,
    sequence_index INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    location TEXT NOT NULL,
    location_label TEXT,
    asset TEXT NOT NULL,
    amount TEXT NOT NULL,
    usd_value TEXT NOT NULL,
    notes TEXT,
    type TEXT NOT NULL,
    subtype TEXT NOT NULL,
    FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
    UNIQUE(event_identifier, sequence_index)
);
"""


# Table that extends history_events table and stores data specific to evm events.
DB_CREATE_EVM_EVENTS_INFO = """
CREATE TABLE IF NOT EXISTS evm_events_info(
    identifier INTEGER PRIMARY KEY,
    tx_hash BLOB NOT NULL,
    counterparty TEXT,
    product TEXT,
    address TEXT,
    extra_data TEXT,
    FOREIGN KEY(identifier) REFERENCES history_events(identifier) ON UPDATE CASCADE ON DELETE CASCADE
);
"""  # noqa: E501

# Table that extends history events table and stores data specific to ethereum staking
DB_CREATE_ETH_STAKING_EVENTS_INFO = """
CREATE TABLE IF NOT EXISTS eth_staking_events_info(
    identifier INTEGER PRIMARY KEY,
    validator_index INTEGER NOT NULL,
    is_exit_or_blocknumber INTEGER NOT NULL,
    FOREIGN KEY(identifier) REFERENCES history_events(identifier) ON UPDATE CASCADE ON DELETE CASCADE
);
"""  # noqa: E501


# This table is used to store for specific history events:
# - whether it is customized
# - validator mapping
DB_CREATE_HISTORY_EVENTS_MAPPINGS = """
CREATE TABLE IF NOT EXISTS history_events_mappings (
    parent_identifier INTEGER NOT NULL,
    name TEXT NOT NULL,
    value INTEGER NOT NULL,
    FOREIGN KEY(parent_identifier) references history_events(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (parent_identifier, name, value)
);
"""  # noqa: E501

DB_CREATE_BALANCER_EVENTS = """
CREATE TABLE IF NOT EXISTS balancer_events (
    tx_hash BLOB NOT NULL,
    log_index INTEGER NOT NULL,
    address VARCHAR[42] NOT NULL,
    timestamp INTEGER NOT NULL,
    type TEXT NOT NULL,
    pool_address_token TEXT NOT NULL,
    lp_amount TEXT NOT NULL,
    usd_value TEXT NOT NULL,
    amount0 TEXT NOT NULL,
    amount1 TEXT NOT NULL,
    amount2 TEXT,
    amount3 TEXT,
    amount4 TEXT,
    amount5 TEXT,
    amount6 TEXT,
    amount7 TEXT,
    FOREIGN KEY (pool_address_token) REFERENCES assets(identifier) ON UPDATE CASCADE,
    PRIMARY KEY (tx_hash, log_index)
);
"""

DB_CREATE_NFTS = """
CREATE TABLE IF NOT EXISTS nfts (
    identifier TEXT NOT NULL PRIMARY KEY,
    name TEXT,
    last_price TEXT,
    last_price_asset TEXT,
    manual_price INTEGER NOT NULL CHECK (manual_price IN (0, 1)),
    owner_address TEXT,
    blockchain TEXT GENERATED ALWAYS AS ('ETH') VIRTUAL,
    is_lp INTEGER NOT NULL CHECK (is_lp IN (0, 1)),
    image_url TEXT,
    collection_name TEXT,
    FOREIGN KEY(blockchain, owner_address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE,
    FOREIGN KEY (identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
    FOREIGN KEY (last_price_asset) REFERENCES assets(identifier) ON UPDATE CASCADE
);
"""  # noqa: E501


DB_CREATE_ENS_MAPPINGS = """
CREATE TABLE IF NOT EXISTS ens_mappings (
    address TEXT NOT NULL PRIMARY KEY,
    ens_name TEXT UNIQUE,
    last_update INTEGER NOT NULL,
    last_avatar_update INTEGER NOT NULL DEFAULT 0
);
"""

DB_CREATE_ADDRESS_BOOK = """
CREATE TABLE IF NOT EXISTS address_book (
    address TEXT NOT NULL,
    blockchain TEXT,
    name TEXT NOT NULL,
    PRIMARY KEY(address, blockchain)
);
"""

DB_CREATE_RPC_NODES = """
CREATE TABLE IF NOT EXISTS rpc_nodes(
    identifier INTEGER NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    owned INTEGER NOT NULL CHECK (owned IN (0, 1)),
    active INTEGER NOT NULL CHECK (active IN (0, 1)),
    weight TEXT NOT NULL,
    blockchain TEXT NOT NULL
);
"""

DB_CREATE_USER_NOTES = """
CREATE TABLE IF NOT EXISTS user_notes(
    identifier INTEGER NOT NULL PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    location TEXT NOT NULL,
    last_update_timestamp INTEGER NOT NULL,
    is_pinned INTEGER NOT NULL CHECK (is_pinned IN (0, 1))
);
"""

DB_SCRIPT_CREATE_TABLES = f"""
PRAGMA foreign_keys=off;
BEGIN TRANSACTION;
{DB_CREATE_TRADE_TYPE}
{DB_CREATE_LOCATION}
{DB_CREATE_ASSET_MOVEMENT_CATEGORY}
{DB_CREATE_BALANCE_CATEGORY}
{DB_CREATE_ASSETS}
{DB_CREATE_TIMED_BALANCES}
{DB_CREATE_TIMED_LOCATION_DATA}
{DB_CREATE_USER_CREDENTIALS}
{DB_CREATE_USER_CREDENTIALS_MAPPINGS}
{DB_CREATE_EXTERNAL_SERVICE_CREDENTIALS}
{DB_CREATE_BLOCKCHAIN_ACCOUNTS}
{DB_CREATE_EVM_ACCOUNTS_DETAILS}
{DB_CREATE_MULTISETTINGS}
{DB_CREATE_MANUALLY_TRACKED_BALANCES}
{DB_CREATE_TRADES}
{DB_CREATE_EVM_TRANSACTIONS}
{DB_CREATE_OPTIMISM_TRANSACTIONS}
{DB_CREATE_EVM_INTERNAL_TRANSACTIONS}
{DB_CREATE_EVMTX_RECEIPTS}
{DB_CREATE_EVMTX_RECEIPT_LOGS}
{DB_CREATE_EVMTX_RECEIPT_LOG_TOPICS}
{DB_CREATE_EVMTX_ADDRESS_MAPPINGS}
{DB_CREATE_MARGIN}
{DB_CREATE_ASSET_MOVEMENTS}
{DB_CREATE_USED_QUERY_RANGES}
{DB_CREATE_EVM_TX_MAPPINGS}
{DB_CREATE_SETTINGS}
{DB_CREATE_TAGS_TABLE}
{DB_CREATE_TAG_MAPPINGS}
{DB_CREATE_YEARN_VAULT_EVENTS}
{DB_CREATE_XPUBS}
{DB_CREATE_XPUB_MAPPINGS}
{DB_CREATE_ETH2_VALIDATORS}
{DB_CREATE_ETH2_DAILY_STAKING_DETAILS}
{DB_CREATE_HISTORY_EVENTS}
{DB_CREATE_EVM_EVENTS_INFO}
{DB_CREATE_ETH_STAKING_EVENTS_INFO}
{DB_CREATE_HISTORY_EVENTS_MAPPINGS}
{DB_CREATE_LEDGER_ACTION_TYPE}
{DB_CREATE_LEDGER_ACTIONS}
{DB_CREATE_ACTION_TYPE}
{DB_CREATE_IGNORED_ACTIONS}
{DB_CREATE_BALANCER_EVENTS}
{DB_CREATE_NFTS}
{DB_CREATE_ENS_MAPPINGS}
{DB_CREATE_ADDRESS_BOOK}
{DB_CREATE_RPC_NODES}
{DB_CREATE_USER_NOTES}
COMMIT;
PRAGMA foreign_keys=on;
"""
