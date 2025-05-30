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
/* ARBITRUM_ONE */
INSERT OR IGNORE INTO location(location, seq) VALUES ('i', 41);
/* BASE */
INSERT OR IGNORE INTO location(location, seq) VALUES ('j', 42);
/* GNOSIS */
INSERT OR IGNORE INTO location(location, seq) VALUES ('k', 43);
/* WOO */
INSERT OR IGNORE INTO location(location, seq) VALUES ('l', 44);
/* Bybit */
INSERT OR IGNORE INTO location(location, seq) VALUES ('m', 45);
/* Scroll */
INSERT OR IGNORE INTO location(location, seq) VALUES ('n', 46);
/* ZKSync Lite */
INSERT OR IGNORE INTO location(location, seq) VALUES ('o', 47);
/* HTX */
INSERT OR IGNORE INTO location(location, seq) VALUES ('p', 48);
/* Bitcoin */
INSERT OR IGNORE INTO location(location, seq) VALUES ('q', 49);
/* Bitcoin Cash */
INSERT OR IGNORE INTO location(location, seq) VALUES ('r', 50);
/* Polkadot */
INSERT OR IGNORE INTO location(location, seq) VALUES ('s', 51);
/* Kusama */
INSERT OR IGNORE INTO location(location, seq) VALUES ('t', 52);
/* Coinbase Prime */
INSERT OR IGNORE INTO location(location, seq) VALUES ('u', 53);
/* Binance Smart Chain */
INSERT OR IGNORE INTO location(location, seq) VALUES ('v', 54);
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

DB_CREATE_ASSETS = """
CREATE TABLE IF NOT EXISTS assets (
    identifier TEXT NOT NULL PRIMARY KEY
);
"""

DB_CREATE_IGNORED_ACTIONS = """
CREATE TABLE IF NOT EXISTS ignored_actions (
    identifier TEXT PRIMARY KEY
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

DB_CREATE_EXTERNAL_SERVICE_CREDENTIALS = """
CREATE TABLE IF NOT EXISTS external_service_credentials (
    name VARCHAR[30] NOT NULL PRIMARY KEY,
    api_key TEXT NOT NULL,
    api_secret TEXT
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

# The table can be used by any L2 chain that has an extra L1 fee structure
# It should be renamed, at some point, to something like `l2_with_l1_fees_transactions`
DB_CREATE_OPTIMISM_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS optimism_transactions (
    tx_id INTEGER NOT NULL PRIMARY KEY,
    l1_fee TEXT,
    FOREIGN KEY(tx_id) REFERENCES evm_transactions(identifier) ON DELETE CASCADE ON UPDATE CASCADE
);
"""

DB_CREATE_EVM_TRANSACTION_AUTHORIZATIONS = """
CREATE TABLE IF NOT EXISTS evm_transactions_authorizations (
    tx_id INTEGER NOT NULL PRIMARY KEY,
    nonce INTEGER NOT NULL,
    delegated_address TEXT NOT NULL,
    FOREIGN KEY(tx_id) REFERENCES evm_transactions(identifier) ON DELETE CASCADE
);
"""

# from/to address/value is also in the primary key of the internal transactions since
# trace_id, which is returned by etherscan does not guarantee uniqueness. Example:
# https://api.etherscan.io/api?module=account&action=txlistinternal&sort=asc&startBlock=16779092&endBlock=16779092
# Same for gas/gas_used. An example would be https://etherscan.io/tx/0x72f5e619a8f521d874652ec5c09ea22e329ed3a990012e1fe6548d5a07e1959c
# where each consolidation internal transaction of 1 wei is the same and can only differentiate
# from gas/gasused combination
# NB: If you change the internal transactions schema then make sure to change the indexes
# at DBHandler.write_tuples are correct
DB_CREATE_EVM_INTERNAL_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS evm_internal_transactions (
    parent_tx INTEGER NOT NULL,
    trace_id INTEGER NOT NULL,
    from_address TEXT NOT NULL,
    to_address TEXT,
    value TEXT NOT NULL,
    gas TEXT NOT NULL,
    gas_used TEXT NOT NULL,
    FOREIGN KEY(parent_tx) REFERENCES evm_transactions(identifier) ON DELETE CASCADE ON UPDATE CASCADE,
    PRIMARY KEY(parent_tx, trace_id, from_address, to_address, value, gas, gas_used)
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

DB_CREATE_EVMTX_ADDRESS_MAPPINGS = """
CREATE TABLE IF NOT EXISTS evmtx_address_mappings (
    tx_id INTEGER NOT NULL,
    address TEXT NOT NULL,
    FOREIGN KEY(tx_id) references evm_transactions(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (tx_id, address)
);
"""


# Custom enum table for zksyn transaction types
DB_CREATE_ZKSYNCLITE_TX_TYPE = """
CREATE TABLE IF NOT EXISTS zksynclite_tx_type (
  type    CHAR(1)       PRIMARY KEY NOT NULL,
  seq     INTEGER UNIQUE
);
/* Transfer Type */
INSERT OR IGNORE INTO zksynclite_tx_type(type, seq) VALUES ('A', 1);
/* Deposit Type */
INSERT OR IGNORE INTO zksynclite_tx_type(type, seq) VALUES ('B', 2);
/* Withdraw Type */
INSERT OR IGNORE INTO zksynclite_tx_type(type, seq) VALUES ('C', 3);
/* ChangePubKey Type */
INSERT OR IGNORE INTO zksynclite_tx_type(type, seq) VALUES ('D', 4);
/* ForcedExit Type */
INSERT OR IGNORE INTO zksynclite_tx_type(type, seq) VALUES ('E', 5);
/* FullExit Type */
INSERT OR IGNORE INTO zksynclite_tx_type(type, seq) VALUES ('F', 6);
/* Swap Type */
INSERT OR IGNORE INTO zksynclite_tx_type(type, seq) VALUES ('G', 7);
"""

# Instead of using an attribute mapping like evm chains adding the is_decoded directly to the table
# Reasoning is it's the only mapping we care for so no reason to keep a different
# mappings table for zksync lite transactions
DB_CREATE_ZKSYNCLITE_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS zksynclite_transactions (
    identifier INTEGER NOT NULL PRIMARY KEY,
    tx_hash BLOB NOT NULL UNIQUE,
    type CHAR(1) NOT NULL DEFAULT('A') REFERENCES zksynclite_tx_type(type),
    is_decoded INTEGER NOT NULL DEFAULT 0 CHECK (is_decoded IN (0, 1)),
    timestamp INTEGER NOT NULL,
    block_number INTEGER NOT NULL,
    from_address TEXT NOT NULL,
    to_address TEXT,
    asset TEXT NOT NULL,
    amount TEXT NOT NULL,
    fee TEXT,
    FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE
);
"""

DB_CREATE_ZKSYNCLITE_SWAPS = """
CREATE TABLE IF NOT EXISTS zksynclite_swaps (
    tx_id INTEGER NOT NULL,
    from_asset TEXT NOT NULL,
    from_amount TEXT NOT NULL,
    to_asset TEXT NOT NULL,
    to_amount TEXT_NOT NULL,
    FOREIGN KEY(tx_id) REFERENCES zksynclite_transactions(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY(from_asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
    FOREIGN KEY(to_asset) REFERENCES assets(identifier) ON UPDATE CASCADE
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
    tx_id INTEGER NOT NULL,
    value INTEGER NOT NULL,
    FOREIGN KEY(tx_id) references evm_transactions(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (tx_id, value)
);
"""

DB_CREATE_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    name VARCHAR[24] NOT NULL PRIMARY KEY,
    value TEXT
);
"""

DB_CREATE_ETH2_VALIDATORS = """
CREATE TABLE IF NOT EXISTS eth2_validators (
    identifier INTEGER NOT NULL PRIMARY KEY,
    validator_index INTEGER UNIQUE,
    public_key TEXT NOT NULL UNIQUE,
    ownership_proportion TEXT NOT NULL,
    withdrawal_address TEXT,
    validator_type INTEGER NOT NULL CHECK (validator_type IN (0, 1, 2)),
    activation_timestamp INTEGER,
    withdrawable_timestamp INTEGER,
    exited_timestamp INTEGER
);
"""

DB_CREATE_ETH_VALIDATORS_DATA_CACHE = """
CREATE TABLE IF NOT EXISTS eth_validators_data_cache (
    id INTEGER NOT NULL PRIMARY KEY,
    validator_index INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,  -- timestamp is in milliseconds
    balance TEXT NOT NULL,
    withdrawals_pnl TEXT NOT NULL,
    exit_pnl TEXT NOT NULL,
    UNIQUE(validator_index, timestamp),
    FOREIGN KEY(validator_index) REFERENCES eth2_validators(validator_index) ON UPDATE CASCADE ON DELETE CASCADE
);
"""  # noqa: E501

DB_CREATE_ETH2_DAILY_STAKING_DETAILS = """
CREATE TABLE IF NOT EXISTS  eth2_daily_staking_details (
    validator_index INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    pnl TEXT NOT NULL,
    FOREIGN KEY(validator_index) REFERENCES eth2_validators(validator_index) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (validator_index, timestamp)
);
"""  # noqa: E501


DB_CREATE_SKIPPED_EXTERNAL_EVENTS = """
CREATE TABLE IF NOT EXISTS skipped_external_events (
    identifier INTEGER NOT NULL PRIMARY KEY,
    data TEXT NOT NULL,
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    extra_data TEXT,
    UNIQUE(data, location)
);
"""

DB_CREATE_HISTORY_EVENTS = """
CREATE TABLE IF NOT EXISTS history_events (
    identifier INTEGER NOT NULL PRIMARY KEY,
    entry_type INTEGER NOT NULL,
    event_identifier TEXT NOT NULL,
    sequence_index INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    location_label TEXT,
    asset TEXT NOT NULL,
    amount TEXT NOT NULL,
    notes TEXT,
    type TEXT NOT NULL,
    subtype TEXT NOT NULL,
    extra_data TEXT,
    ignored INTEGER NOT NULL DEFAULT 0,
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


# usd_price is a column of the table because we sort by price in the fiat currency and that price
# needs to be calculated from last_price and the price of last_price_asset. If we don't sort using
# the usd_price when the NFTs are valued in different assets the order is not correct.
DB_CREATE_NFTS = """
CREATE TABLE IF NOT EXISTS nfts (
    identifier TEXT NOT NULL PRIMARY KEY,
    name TEXT,
    last_price TEXT NOT NULL,
    last_price_asset TEXT NOT NULL,
    manual_price INTEGER NOT NULL CHECK (manual_price IN (0, 1)),
    owner_address TEXT,
    blockchain TEXT GENERATED ALWAYS AS ('ETH') VIRTUAL,
    is_lp INTEGER NOT NULL CHECK (is_lp IN (0, 1)),
    image_url TEXT,
    collection_name TEXT,
    usd_price REAL NOT NULL DEFAULT 0,
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
    blockchain TEXT NOT NULL,
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
    blockchain TEXT NOT NULL,
    UNIQUE(endpoint, blockchain)
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

DB_CREATE_ACCOUNTING_RULE = """
CREATE TABLE IF NOT EXISTS accounting_rules(
    identifier INTEGER NOT NULL PRIMARY KEY,
    type TEXT NOT NULL,
    subtype TEXT NOT NULL,
    counterparty TEXT NOT NULL,
    taxable INTEGER NOT NULL CHECK (taxable IN (0, 1)),
    count_entire_amount_spend INTEGER NOT NULL CHECK (count_entire_amount_spend IN (0, 1)),
    count_cost_basis_pnl INTEGER NOT NULL CHECK (count_cost_basis_pnl IN (0, 1)),
    accounting_treatment TEXT,
    UNIQUE(type, subtype, counterparty)
);
"""

DB_CREATE_MAPPED_ACCOUNTING_RULES = """
CREATE TABLE IF NOT EXISTS linked_rules_properties(
    identifier INTEGER PRIMARY KEY NOT NULL,
    accounting_rule INTEGER REFERENCES accounting_rules(identifier),
    property_name TEXT NOT NULL,
    setting_name TEXT NOT NULL references settings(name)
);
"""

DB_CREATE_UNRESOLVED_REMOTE_CONFLICTS = """
CREATE TABLE IF NOT EXISTS unresolved_remote_conflicts(
    identifier INTEGER PRIMARY KEY NOT NULL,
    local_id INTEGER NOT NULL,
    remote_data TEXT NOT NULL,
    type INTEGER NOT NULL
);
"""

DB_CREATE_KEY_VALUE_CACHE = """CREATE TABLE IF NOT EXISTS key_value_cache (
    name TEXT NOT NULL PRIMARY KEY,
    value TEXT
);"""


DB_CREATE_CALENDAR = """
CREATE TABLE IF NOT EXISTS calendar (
    identifier INTEGER PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    description TEXT,
    counterparty TEXT,
    address TEXT,
    blockchain TEXT,
    color TEXT,
    auto_delete INTEGER NOT NULL CHECK (auto_delete IN (0, 1)),
    FOREIGN KEY(blockchain, address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE,
    UNIQUE(name, address, blockchain)
);
"""  # noqa: E501


DB_CREATE_CALENDAR_REMINDERS = """
CREATE TABLE IF NOT EXISTS calendar_reminders (
    identifier INTEGER PRIMARY KEY NOT NULL,
    event_id INTEGER NOT NULL,
    secs_before INTEGER NOT NULL,
    acknowledged INTEGER NOT NULL CHECK (acknowledged IN (0, 1)) DEFAULT 0,
    FOREIGN KEY(event_id) REFERENCES calendar(identifier) ON DELETE CASCADE
);
"""

DB_CREATE_COWSWAP_ORDERS = """
CREATE TABLE IF NOT EXISTS cowswap_orders (
    identifier TEXT NOT NULL PRIMARY KEY,
    order_type TEXT NOT NULL,
    raw_fee_amount TEXT NOT NULL
);
"""

DB_CREATE_GNOSISPAY_DATA = """
CREATE TABLE IF NOT EXISTS gnosispay_data (
    identifier INTEGER PRIMARY KEY NOT NULL,
    tx_hash BLOB NOT NULL UNIQUE,
    timestamp INTEGER NOT NULL,
    merchant_name TEXT NOT NULL,
    merchant_city TEXT,
    country TEXT NOT NULL,
    mcc INTEGER NOT NULL,
    transaction_symbol TEXT NOT NULL,
    transaction_amount TEXT NOT NULL,
    billing_symbol TEXT,
    billing_amount TEXT,
    reversal_symbol TEXT,
    reversal_amount TEXT,
    reversal_tx_hash BLOB UNIQUE
);
"""

# The history_events indexes significantly improve performance when filtering history events in large DBs.  # noqa: E501
# TODO: add before/after times for each index from the big user DB.
# Before: 5500ms, After: 7ms
DB_CREATE_ENTRY_TYPE_INDEX = 'CREATE INDEX IF NOT EXISTS idx_history_events_entry_type ON history_events(entry_type);'  # noqa: E501
DB_CREATE_TIMESTAMP_INDEX = 'CREATE INDEX IF NOT EXISTS idx_history_events_timestamp ON history_events(timestamp);'  # noqa: E501
DB_CREATE_LOCATION_INDEX = 'CREATE INDEX IF NOT EXISTS idx_history_events_location ON history_events(location);'  # noqa: E501
DB_CREATE_LOCATION_LABEL_INDEX = 'CREATE INDEX IF NOT EXISTS idx_history_events_location_label ON history_events(location_label);'  # noqa: E501
DB_CREATE_ASSET_INDEX = 'CREATE INDEX IF NOT EXISTS idx_history_events_asset ON history_events(asset);'  # noqa: E501
DB_CREATE_TYPE_INDEX = 'CREATE INDEX IF NOT EXISTS idx_history_events_type ON history_events(type);'  # noqa: E501
DB_CREATE_SUBTYPE_INDEX = 'CREATE INDEX IF NOT EXISTS idx_history_events_subtype ON history_events(subtype);'  # noqa: E501
# Before: ~7sec, After ~3.8sec
DB_CREATE_IGNORED_INDEX = 'CREATE INDEX IF NOT EXISTS idx_history_events_ignored ON history_events(ignored);'  # noqa: E501

DB_SCRIPT_CREATE_TABLES = f"""
PRAGMA foreign_keys=off;
BEGIN TRANSACTION;
{DB_CREATE_LOCATION}
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
{DB_CREATE_EVM_TRANSACTIONS}
{DB_CREATE_EVM_TRANSACTION_AUTHORIZATIONS}
{DB_CREATE_OPTIMISM_TRANSACTIONS}
{DB_CREATE_EVM_INTERNAL_TRANSACTIONS}
{DB_CREATE_EVMTX_RECEIPTS}
{DB_CREATE_EVMTX_RECEIPT_LOGS}
{DB_CREATE_EVMTX_RECEIPT_LOG_TOPICS}
{DB_CREATE_EVMTX_ADDRESS_MAPPINGS}
{DB_CREATE_ZKSYNCLITE_TX_TYPE}
{DB_CREATE_ZKSYNCLITE_TRANSACTIONS}
{DB_CREATE_ZKSYNCLITE_SWAPS}
{DB_CREATE_MARGIN}
{DB_CREATE_USED_QUERY_RANGES}
{DB_CREATE_EVM_TX_MAPPINGS}
{DB_CREATE_SETTINGS}
{DB_CREATE_TAGS_TABLE}
{DB_CREATE_TAG_MAPPINGS}
{DB_CREATE_XPUBS}
{DB_CREATE_XPUB_MAPPINGS}
{DB_CREATE_ETH2_VALIDATORS}
{DB_CREATE_ETH_VALIDATORS_DATA_CACHE}
{DB_CREATE_ETH2_DAILY_STAKING_DETAILS}
{DB_CREATE_HISTORY_EVENTS}
{DB_CREATE_EVM_EVENTS_INFO}
{DB_CREATE_ETH_STAKING_EVENTS_INFO}
{DB_CREATE_HISTORY_EVENTS_MAPPINGS}
{DB_CREATE_IGNORED_ACTIONS}
{DB_CREATE_NFTS}
{DB_CREATE_ENS_MAPPINGS}
{DB_CREATE_ADDRESS_BOOK}
{DB_CREATE_RPC_NODES}
{DB_CREATE_USER_NOTES}
{DB_CREATE_SKIPPED_EXTERNAL_EVENTS}
{DB_CREATE_ACCOUNTING_RULE}
{DB_CREATE_MAPPED_ACCOUNTING_RULES}
{DB_CREATE_UNRESOLVED_REMOTE_CONFLICTS}
{DB_CREATE_KEY_VALUE_CACHE}
{DB_CREATE_CALENDAR}
{DB_CREATE_CALENDAR_REMINDERS}
{DB_CREATE_COWSWAP_ORDERS}
{DB_CREATE_GNOSISPAY_DATA}
{DB_CREATE_ENTRY_TYPE_INDEX}
{DB_CREATE_TIMESTAMP_INDEX}
{DB_CREATE_LOCATION_INDEX}
{DB_CREATE_LOCATION_LABEL_INDEX}
{DB_CREATE_ASSET_INDEX}
{DB_CREATE_TYPE_INDEX}
{DB_CREATE_SUBTYPE_INDEX}
{DB_CREATE_IGNORED_INDEX}
COMMIT;
PRAGMA foreign_keys=on;
"""
