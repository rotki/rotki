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
    time INTEGER,
    currency VARCHAR[12],
    amount TEXT,
    usd_value TEXT,
    PRIMARY KEY (time, currency, category)
);
"""

DB_CREATE_TIMED_LOCATION_DATA = """
CREATE TABLE IF NOT EXISTS timed_location_data (
    time INTEGER,
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    usd_value TEXT,
    PRIMARY KEY (time, location)
);
"""

DB_CREATE_USER_CREDENTIALS = """
CREATE TABLE IF NOT EXISTS user_credentials (
    name VARCHAR[24] NOT NULL PRIMARY KEY,
    api_key TEXT,
    api_secret TEXT,
    passphrase TEXT
);
"""

DB_CREATE_AAVE_EVENTS = """
CREATE TABLE IF NOT EXISTS aave_events (
    address VARCHAR[42] NOT NULL,
    event_type VARCHAR[10] NOT NULL,
    block_number INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    tx_hash VARCHAR[66] NOT NULL,
    log_index INTEGER NOT NULL,
    asset1 VARCHAR[12] NOT NULL,
    asset1_amount TEXT NOT NULL,
    asset1_usd_value TEXT NOT NULL,
    asset2 VARCHAR[12],
    asset2amount_borrowrate_feeamount TEXT,
    asset2usd_value_accruedinterest_feeusdvalue TEXT,
    borrow_rate_mode VARCHAR[10],
    PRIMARY KEY (event_type, tx_hash, log_index)
);
"""

DB_CREATE_YEARN_VAULT_EVENTS = """
CREATE TABLE IF NOT EXISTS yearn_vaults_events (
    address VARCHAR[42] NOT NULL,
    event_type VARCHAR[10] NOT NULL,
    from_asset VARCHAR[44] NOT NULL,
    from_amount TEXT NOT NULL,
    from_usd_value TEXT NOT NULL,
    to_asset VARCHAR[44] NOT NULL,
    to_amount TEXT NOT NULL,
    to_usd_value TEXT NOT NULL,
    pnl_amount TEXT,
    pnl_usd_value TEXT,
    block_number INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    tx_hash VARCHAR[66] NOT NULL,
    log_index INTEGER NOT NULL,
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
    blockchain VARCHAR[24],
    account TEXT NOT NULL PRIMARY KEY,
    label TEXT
);
"""

DB_CREATE_XPUBS = """
CREATE TABLE IF NOT EXISTS xpubs (
    xpub TEXT NOT NULL,
    derivation_path TEXT NOT NULL,
    label TEXT,
    PRIMARY KEY (xpub, derivation_path)
);
"""

DB_CREATE_XPUB_MAPPINGS = """
CREATE TABLE IF NOT EXISTS xpub_mappings (
    address TEXT NOT NULL,
    xpub TEXT NOT NULL,
    derivation_path TEXT NOT NULL,
    account_index INTEGER,
    derived_index INTEGER,
    FOREIGN KEY(address) REFERENCES blockchain_accounts(account) ON DELETE CASCADE
    FOREIGN KEY(xpub, derivation_path) REFERENCES xpubs(xpub, derivation_path) ON DELETE CASCADE
    PRIMARY KEY (address, xpub, derivation_path)
);
"""

DB_CREATE_ETHEREUM_ACCOUNTS_DETAILS = """
CREATE TABLE IF NOT EXISTS ethereum_accounts_details (
    account VARCHAR[42] NOT NULL PRIMARY KEY,
    tokens_list TEXT NOT NULL,
    time INTEGER NOT NULL
);
"""

DB_CREATE_MANUALLY_TRACKED_BALANCES = """
CREATE TABLE IF NOT EXISTS manually_tracked_balances (
    asset VARCHAR[24] NOT NULL,
    label TEXT NOT NULL PRIMARY KEY,
    amount TEXT,
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location)
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
    id TEXT PRIMARY KEY,
    time INTEGER,
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    pair VARCHAR[24],
    type CHAR(1) NOT NULL DEFAULT ('A') REFERENCES trade_type(type),
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
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
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
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    category CHAR(1) NOT NULL DEFAULT('A') REFERENCES asset_movement_category(category),
    address TEXT,
    transaction_id TEXT,
    time INTEGER,
    asset VARCHAR[10],
    amount TEXT,
    fee_asset VARCHAR[10],
    fee TEXT,
    link TEXT
);
"""

DB_CREATE_LEDGER_ACTIONS = """
CREATE TABLE IF NOT EXISTS ledger_actions (
    identifier INTEGER PRIMARY KEY,
    timestamp INTEGER,
    type CHAR(1) NOT NULL DEFAULT('A') REFERENCES ledger_action_type(type),
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    amount TEXT,
    asset VARCHAR[10],
    link TEXT,
    notes TEXT
);
"""

DB_CREATE_ETHEREUM_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS ethereum_transactions (
    tx_hash BLOB,
    timestamp INTEGER,
    block_number INTEGER,
    from_address TEXT,
    to_address TEXT,
    value TEXT,
    gas TEXT,
    gas_price TEXT,
    gas_used TEXT,
    input_data BLOB,
    nonce INTEGER,
    /* we determine uniqueness for ethereum internal transactions by using an
    increasingly negative number */
    PRIMARY KEY (tx_hash, nonce, from_address)
);
"""

DB_CREATE_USED_QUERY_RANGES = """
CREATE TABLE IF NOT EXISTS used_query_ranges (
    name VARCHAR[24] NOT NULL PRIMARY KEY,
    start_ts INTEGER,
    end_ts INTEGER
);
"""

DB_CREATE_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    name VARCHAR[24] NOT NULL PRIMARY KEY,
    value TEXT
);
"""

DB_CREATE_AMM_SWAPS = """
CREATE TABLE IF NOT EXISTS amm_swaps (
    tx_hash VARCHAR[42] NOT NULL,
    log_index INTEGER NOT NULL,
    address VARCHAR[42] NOT NULL,
    from_address VARCHAR[42] NOT NULL,
    to_address VARCHAR[42] NOT NULL,
    timestamp INTEGER NOT NULL,
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    is_token0_unknown INTEGER NOT NULL,
    token0_address VARCHAR[42] NOT NULL,
    token0_symbol TEXT NOT NULL,
    token0_name TEXT,
    token0_decimals INTEGER,
    is_token1_unknown INTEGER NOT NULL,
    token1_address VARCHAR[42] NOT NULL,
    token1_symbol TEXT NOT NULL,
    token1_name TEXT,
    token1_decimals INTEGER,
    amount0_in TEXT,
    amount1_in TEXT,
    amount0_out TEXT,
    amount1_out TEXT,
    PRIMARY KEY (tx_hash, log_index)
);
"""

DB_CREATE_UNISWAP_EVENTS = """
CREATE TABLE IF NOT EXISTS uniswap_events (
    tx_hash VARCHAR[42] NOT NULL,
    log_index INTEGER NOT NULL,
    address VARCHAR[42] NOT NULL,
    timestamp INTEGER NOT NULL,
    type TEXT NOT NULL,
    pool_address VARCHAR[42] NOT NULL,
    is_token0_unknown INTEGER NOT NULL,
    token0_address VARCHAR[42] NOT NULL,
    token0_symbol TEXT NOT NULL,
    token0_name TEXT,
    token0_decimals INTEGER,
    is_token1_unknown INTEGER NOT NULL,
    token1_address VARCHAR[42] NOT NULL,
    token1_symbol TEXT NOT NULL,
    token1_name TEXT,
    token1_decimals INTEGER,
    amount0 TEXT,
    amount1 TEXT,
    usd_price TEXT,
    lp_amount TEXT,
    PRIMARY KEY (tx_hash, log_index)
);
"""

DB_CREATE_ETH2_DEPOSITS = """
CREATE TABLE IF NOT EXISTS eth2_deposits (
    tx_hash VARCHAR[42] NOT NULL,
    log_index INTEGER NOT NULL,
    from_address VARCHAR[42] NOT NULL,
    timestamp INTEGER NOT NULL,
    pubkey TEXT NOT NULL,
    withdrawal_credentials TEXT NOT NULL,
    amount TEXT NOT NULL,
    usd_value TEXT NOT NULL,
    deposit_index INTEGER NOT NULL,
    PRIMARY KEY (tx_hash, log_index)
);
"""

DB_CREATE_ETH2_DAILY_STAKING_DETAILS = """
CREATE TABLE IF NOT EXISTS eth2_daily_staking_details (
    validator_index INTEGER NOT NULL,
    timestamp integer NOT NULL,
    start_usd_price TEXT NOT NULL,
    end_usd_price TEXT NOT NULL,
    pnl TEXT NOT NULL,
    start_amount TEXT NOT NULL,
    end_amount TEXT NOT NULL,
    missed_attestations INTEGER,
    orphaned_attestations INTEGER,
    proposed_blocks INTEGER,
    missed_blocks INTEGER,
    orphaned_blocks INTEGER,
    included_attester_slashings INTEGER,
    proposer_attester_slashings INTEGER,
    deposits_number INTEGER,
    amount_deposited TEXT,
    PRIMARY KEY (validator_index, timestamp)
);
"""

DB_CREATE_ADEX_EVENTS = """
CREATE TABLE IF NOT EXISTS adex_events (
    tx_hash VARCHAR[42] NOT NULL,
    address VARCHAR[42] NOT NULL,
    identity_address VARCHAR[42] NOT NULL,
    timestamp INTEGER NOT NULL,
    type TEXT NOT NULL,
    pool_id TEXT NOT NULL,
    amount TEXT NOT NULL,
    usd_value TEXT NOT NULL,
    bond_id TEXT,
    nonce INT,
    slashed_at INTEGER,
    unlock_at INTEGER,
    channel_id TEXT,
    token TEXT,
    log_index INTEGER,
    PRIMARY KEY (tx_hash, address, type, log_index)
);
"""

# Balancer pools contain at least 2 tokens
DB_CREATE_BALANCER_POOLS = """
CREATE TABLE IF NOT EXISTS balancer_pools (
    address VARCHAR[42] NOT NULL PRIMARY KEY,
    tokens_number INTEGER NOT NULL,
    is_token0_unknown INTEGER NOT NULL,
    token0_address VARCHAR[42] NOT NULL,
    token0_symbol TEXT NOT NULL,
    token0_name TEXT,
    token0_decimals INTEGER,
    token0_weight TEXT NOT NULL,
    is_token1_unknown INTEGER NOT NULL,
    token1_address VARCHAR[42] NOT NULL,
    token1_symbol TEXT NOT NULL,
    token1_name TEXT,
    token1_decimals INTEGER,
    token1_weight TEXT NOT NULL,
    is_token2_unknown INTEGER,
    token2_address VARCHAR[42],
    token2_symbol TEXT,
    token2_name TEXT,
    token2_decimals INTEGER,
    token2_weight TEXT,
    is_token3_unknown INTEGER,
    token3_address VARCHAR[42],
    token3_symbol TEXT,
    token3_name TEXT,
    token3_decimals INTEGER,
    token3_weight TEXT,
    is_token4_unknown INTEGER,
    token4_address VARCHAR[42],
    token4_symbol TEXT,
    token4_name TEXT,
    token4_decimals INTEGER,
    token4_weight TEXT,
    is_token5_unknown INTEGER,
    token5_address VARCHAR[42],
    token5_symbol TEXT,
    token5_name TEXT,
    token5_decimals INTEGER,
    token5_weight TEXT,
    is_token6_unknown INTEGER,
    token6_address VARCHAR[42],
    token6_symbol TEXT,
    token6_name TEXT,
    token6_decimals INTEGER,
    token6_weight TEXT,
    is_token7_unknown INTEGER,
    token7_address VARCHAR[42],
    token7_symbol TEXT,
    token7_name TEXT,
    token7_decimals INTEGER,
    token7_weight TEXT
);
"""

DB_CREATE_BALANCER_EVENTS = """
CREATE TABLE IF NOT EXISTS balancer_events (
    tx_hash VARCHAR[42] NOT NULL,
    log_index INTEGER NOT NULL,
    address VARCHAR[42] NOT NULL,
    timestamp INTEGER NOT NULL,
    type TEXT NOT NULL,
    pool_address VARCHAR[42] NOT NULL,
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
    FOREIGN KEY (pool_address) REFERENCES balancer_pools(address)
    PRIMARY KEY (tx_hash, log_index)
);
"""

DB_SCRIPT_CREATE_TABLES = """
PRAGMA foreign_keys=off;
BEGIN TRANSACTION;
{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}
COMMIT;
PRAGMA foreign_keys=on;
""".format(
    DB_CREATE_TRADE_TYPE,
    DB_CREATE_LOCATION,
    DB_CREATE_ASSET_MOVEMENT_CATEGORY,
    DB_CREATE_BALANCE_CATEGORY,
    DB_CREATE_TIMED_BALANCES,
    DB_CREATE_TIMED_LOCATION_DATA,
    DB_CREATE_USER_CREDENTIALS,
    DB_CREATE_EXTERNAL_SERVICE_CREDENTIALS,
    DB_CREATE_BLOCKCHAIN_ACCOUNTS,
    DB_CREATE_ETHEREUM_ACCOUNTS_DETAILS,
    DB_CREATE_MULTISETTINGS,
    DB_CREATE_MANUALLY_TRACKED_BALANCES,
    DB_CREATE_TRADES,
    DB_CREATE_ETHEREUM_TRANSACTIONS,
    DB_CREATE_MARGIN,
    DB_CREATE_ASSET_MOVEMENTS,
    DB_CREATE_USED_QUERY_RANGES,
    DB_CREATE_SETTINGS,
    DB_CREATE_TAGS_TABLE,
    DB_CREATE_TAG_MAPPINGS,
    DB_CREATE_AAVE_EVENTS,
    DB_CREATE_YEARN_VAULT_EVENTS,
    DB_CREATE_XPUBS,
    DB_CREATE_XPUB_MAPPINGS,
    DB_CREATE_AMM_SWAPS,
    DB_CREATE_UNISWAP_EVENTS,
    DB_CREATE_ETH2_DEPOSITS,
    DB_CREATE_ETH2_DAILY_STAKING_DETAILS,
    DB_CREATE_ADEX_EVENTS,
    DB_CREATE_LEDGER_ACTION_TYPE,
    DB_CREATE_LEDGER_ACTIONS,
    DB_CREATE_ACTION_TYPE,
    DB_CREATE_IGNORED_ACTIONS,
    DB_CREATE_BALANCER_POOLS,
    DB_CREATE_BALANCER_EVENTS,
)
