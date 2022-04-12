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
    time INTEGER,
    currency TEXT,
    amount TEXT,
    usd_value TEXT,
    FOREIGN KEY(currency) REFERENCES assets(identifier) ON UPDATE CASCADE,
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

DB_CREATE_AAVE_EVENTS = """
CREATE TABLE IF NOT EXISTS aave_events (
    address VARCHAR[42] NOT NULL,
    event_type VARCHAR[10] NOT NULL,
    block_number INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    tx_hash VARCHAR[66] NOT NULL,
    log_index INTEGER NOT NULL,
    asset1 TEXT NOT NULL,
    asset1_amount TEXT NOT NULL,
    asset1_usd_value TEXT NOT NULL,
    asset2 TEXT,
    asset2amount_borrowrate_feeamount TEXT,
    asset2usd_value_accruedinterest_feeusdvalue TEXT,
    borrow_rate_mode VARCHAR[10],
    FOREIGN KEY(asset1) REFERENCES assets(identifier) ON UPDATE CASCADE,
    FOREIGN KEY(asset2) REFERENCES assets(identifier) ON UPDATE CASCADE,
    PRIMARY KEY (event_type, tx_hash, log_index)
);
"""

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
    tx_hash VARCHAR[66] NOT NULL,
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
    blockchain TEXT GENERATED ALWAYS AS ("BTC") VIRTUAL,
    FOREIGN KEY(blockchain, address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE
    FOREIGN KEY(xpub, derivation_path) REFERENCES xpubs(xpub, derivation_path) ON DELETE CASCADE
    PRIMARY KEY (address, xpub, derivation_path)
);
"""  # noqa: E501

DB_CREATE_ETHEREUM_ACCOUNTS_DETAILS = """
CREATE TABLE IF NOT EXISTS ethereum_accounts_details (
    account VARCHAR[42] NOT NULL PRIMARY KEY,
    tokens_list TEXT NOT NULL,
    time INTEGER NOT NULL
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
    time INTEGER NOT NULL,
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
    time INTEGER,
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

DB_CREATE_ETHEREUM_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS ethereum_transactions (
    tx_hash BLOB NOT NULL PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    block_number INTEGER NOT NULL,
    from_address TEXT NOT NULL,
    to_address TEXT,
    value TEXT NOT NULL,
    gas TEXT NOT NULL,
    gas_price TEXT NOT NULL,
    gas_used TEXT NOT NULL,
    input_data BLOB NOT NULL,
    nonce INTEGER NOT NULL
);
"""

DB_CREATE_ETHEREUM_INTERNAL_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS ethereum_internal_transactions (
    parent_tx_hash BLOB NOT NULL,
    trace_id INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    block_number INTEGER NOT NULL,
    from_address TEXT NOT NULL,
    to_address TEXT,
    value TEXT NOT NULL,
    FOREIGN KEY(parent_tx_hash) REFERENCES ethereum_transactions(tx_hash) ON DELETE CASCADE ON UPDATE CASCADE,
    PRIMARY KEY(parent_tx_hash, trace_id)
);
"""  # noqa: E501

DB_CREATE_ETHTX_RECEIPTS = """
CREATE TABLE IF NOT EXISTS ethtx_receipts (
    tx_hash BLOB NOT NULL PRIMARY KEY,
    contract_address TEXT, /* can be null */
    status INTEGER NOT NULL CHECK (status IN (0, 1)),
    type INTEGER NOT NULL,
    FOREIGN KEY(tx_hash) REFERENCES ethereum_transactions(tx_hash) ON DELETE CASCADE ON UPDATE CASCADE
);
"""  # noqa: E501

DB_CREATE_ETHTX_RECEIPT_LOGS = """
CREATE TABLE IF NOT EXISTS ethtx_receipt_logs (
    tx_hash BLOB NOT NULL,
    log_index INTEGER NOT NULL,
    data BLOB NOT NULL,
    address TEXT NOT NULL,
    removed INTEGER NOT NULL CHECK (removed IN (0, 1)),
    FOREIGN KEY(tx_hash) REFERENCES ethtx_receipts(tx_hash) ON DELETE CASCADE ON UPDATE CASCADE,
    PRIMARY KEY(tx_hash, log_index)
);
"""

DB_CREATE_ETHTX_RECEIPT_LOG_TOPICS = """
CREATE TABLE IF NOT EXISTS ethtx_receipt_log_topics (
    tx_hash BLOB NOT NULL,
    log_index INTEGER NOT NULL,
    topic BLOB NOT NULL,
    topic_index INTEGER NOT NULL,
    FOREIGN KEY(tx_hash, log_index) REFERENCES ethtx_receipt_logs(tx_hash, log_index) ON DELETE CASCADE ON UPDATE CASCADE,
    PRIMARY KEY(tx_hash, log_index, topic_index)
);
"""  # noqa: E501

DB_CREATE_ETHTX_ADDRESS_MAPPINGS = """
CREATE TABLE IF NOT EXISTS ethtx_address_mappings (
    address TEXT NOT NULL,
    tx_hash BLOB NOT NULL,
    blockchain TEXT NOT NULL,
    FOREIGN KEY(blockchain, address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE,
    FOREIGN KEY(tx_hash) references ethereum_transactions(tx_hash) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (address, tx_hash, blockchain)
);
"""  # noqa: E501

DB_CREATE_USED_QUERY_RANGES = """
CREATE TABLE IF NOT EXISTS used_query_ranges (
    name VARCHAR[24] NOT NULL PRIMARY KEY,
    start_ts INTEGER,
    end_ts INTEGER
);
"""

DB_CREATE_EVM_TX_MAPPINGS = """
CREATE TABLE IF NOT EXISTS evm_tx_mappings (
    tx_hash BLOB NOT NULL,
    blockchain TEXT NOT NULL,
    value TEXT NOT NULL,
    FOREIGN KEY(tx_hash) references ethereum_transactions(tx_hash) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (tx_hash, value)
);
"""  # noqa: E501

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
    token0_identifier TEXT NOT NULL,
    token1_identifier TEXT NOT NULL,
    amount0_in TEXT,
    amount1_in TEXT,
    amount0_out TEXT,
    amount1_out TEXT,
    FOREIGN KEY(token0_identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
    FOREIGN KEY(token1_identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
    PRIMARY KEY (tx_hash, log_index)
);
"""

DB_CREATE_AMM_EVENTS = """
CREATE TABLE IF NOT EXISTS amm_events (
    tx_hash VARCHAR[42] NOT NULL,
    log_index INTEGER NOT NULL,
    address VARCHAR[42] NOT NULL,
    timestamp INTEGER NOT NULL,
    type TEXT NOT NULL,
    pool_address VARCHAR[42] NOT NULL,
    token0_identifier TEXT NOT NULL,
    token1_identifier TEXT NOT NULL,
    amount0 TEXT,
    amount1 TEXT,
    usd_price TEXT,
    lp_amount TEXT,
    FOREIGN KEY(token0_identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
    FOREIGN KEY(token1_identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
    PRIMARY KEY (tx_hash, log_index)
);
"""

DB_CREATE_ETH2_VALIDATORS = """
CREATE TABLE IF NOT EXISTS eth2_validators (
    validator_index INTEGER NOT NULL PRIMARY KEY,
    public_key TEXT NOT NULL UNIQUE,
    ownership_proportion TEXT NOT NULL
);
"""

DB_CREATE_ETH2_DEPOSITS = """
CREATE TABLE IF NOT EXISTS eth2_deposits (
    tx_hash BLOB NOT NULL,
    tx_index INTEGER NOT NULL,
    from_address VARCHAR[42] NOT NULL,
    timestamp INTEGER NOT NULL,
    pubkey TEXT NOT NULL,
    withdrawal_credentials TEXT NOT NULL,
    amount TEXT NOT NULL,
    usd_value TEXT NOT NULL,
    FOREIGN KEY(pubkey) REFERENCES eth2_validators(public_key) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY(tx_hash, pubkey, amount) /* multiple deposits can exist for same pubkey */
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
    FOREIGN KEY(validator_index) REFERENCES eth2_validators(validator_index) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (validator_index, timestamp)
);
"""  # noqa: E501

DB_CREATE_HISTORY_EVENTS = """
CREATE TABLE IF NOT EXISTS history_events (
    identifier INTEGER NOT NULL PRIMARY KEY,
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
    subtype TEXT,
    counterparty TEXT,
    UNIQUE(event_identifier, sequence_index)
);
"""

DB_CREATE_HISTORY_EVENTS_MAPPINGS = """
CREATE TABLE IF NOT EXISTS history_events_mappings (
    parent_identifier INTEGER NOT NULL,
    value TEXT NOT NULL,
    FOREIGN KEY(parent_identifier) references history_events(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (parent_identifier, value)
);
"""  # noqa: E501

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
    FOREIGN KEY(token) REFERENCES assets(identifier) ON UPDATE CASCADE,
    PRIMARY KEY (tx_hash, address, type, log_index)
);
"""

DB_CREATE_BALANCER_EVENTS = """
CREATE TABLE IF NOT EXISTS balancer_events (
    tx_hash VARCHAR[42] NOT NULL,
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
    blockchain TEXT GENERATED ALWAYS AS ("ETH") VIRTUAL,
    FOREIGN KEY(blockchain, owner_address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE,
    FOREIGN KEY (identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
    FOREIGN KEY (last_price_asset) REFERENCES assets(identifier) ON UPDATE CASCADE
);
"""  # noqa: E501

DB_CREATE_COMBINED_TRADES_VIEW = """
CREATE VIEW IF NOT EXISTS combined_trades_view AS
    WITH amounts_query AS (
          SELECT
          A.tx_hash AS txhash,
          A.log_index AS logindex,
          A.timestamp AS time,
          A.location AS location,
          FE.amount1_in AS first1in,
          FE.amount0_in AS first0in,
          FE.token0_identifier AS firsttoken0,
          FE.token1_identifier AS firsttoken1,
          LE.amount0_out AS last0out,
          LE.amount1_out AS last1out,
          LE.token0_identifier AS lasttoken0,
          LE.token1_identifier AS lasttoken1
          FROM amm_swaps A
          LEFT JOIN amm_swaps FE ON
          FE.tx_hash = A.tx_hash AND FE.log_index=(SELECT MIN(log_index) FROM amm_swaps WHERE tx_hash=A.tx_hash)
          LEFT JOIN amm_swaps LE ON
          LE.tx_hash = A.tx_hash AND LE.log_index=(SELECT MAX(log_index) FROM amm_swaps WHERE tx_hash=A.tx_hash)
          WHERE A.tx_hash IN (SELECT DISTINCT tx_hash FROM amm_swaps) GROUP BY A.tx_hash
    ), C1 AS (
        SELECT lasttoken0 AS base1, firsttoken0 AS quote1, last0out AS amount1, cast(first0in AS REAL) / CAST(last0out AS REAL) AS rate1, txhash, logindex, time, location
        FROM amounts_query
        WHERE first0in > 0 AND last0out > 0 AND first1in == 0 AND last1out == 0
    ), C2 AS (
        SELECT lasttoken1 AS base1, firsttoken0 AS quote1, last1out AS amount1, cast(first0in AS REAL) / CAST(last1out AS REAL) AS rate1, txhash, logindex, time, location
        FROM amounts_query
        WHERE first0in > 0 AND last1out > 0 AND first1in == 0 AND last0out == 0
    ), C3 AS (
        SELECT lasttoken0 AS base1, firsttoken1 AS quote1, last0out AS amount1, CAST(first1in AS REAL) / CAST(last0out AS REAL) AS rate1, txhash, logindex, time, location
        FROM amounts_query
        WHERE first1in > 0 AND last0out > 0 AND first0in == 0 AND last1out == 0
    ), C4 AS (
        SELECT lasttoken1 AS base1, firsttoken1 AS quote1, last1out AS amount1, CAST(first1in AS REAL) / CAST(last1out AS REAL) AS rate1, txhash, logindex, time, location
        FROM amounts_query
        WHERE first1in > 0 AND last1out > 0 AND first0in == 0 AND last0out == 0
    ), C5 AS (
        SELECT
            lasttoken1 AS base1,
            firsttoken1 AS quote1,
            (CAST(last1out AS REAL) / 2) AS amount1,
            CAST(first1in AS REAL) / (CAST(last1out AS REAL) / 2) as rate1,
            lasttoken1 AS base2,
            firsttoken0 AS quote2,
            (CAST(last1out AS REAL) / 2) AS amount2,
            CAST(first0in AS REAL) / (CAST(last1out AS REAL) / 2) AS rate2,
            txhash, logindex, time, location
        FROM amounts_query
        WHERE first1in > 0 AND first0in > 0 AND last1out > 0 AND last0out == 0
    ), C6 AS (
        SELECT
            lasttoken1 AS base1,
            firsttoken1 AS quote1,
            last1out AS amount1,
            CAST(first1in AS REAL) / CAST(last1out AS REAL) AS rate1,
            lasttoken0 AS base2,
            firsttoken0 AS quote2,
            last0out AS amount2,
            CAST(first0in AS REAL) / CAST(last0out AS REAL) AS rate2,
            txhash, logindex, time, location
        FROM amounts_query
        WHERE first1in > 0 AND first0in > 0 AND last1out > 0 AND last0out > 0
    ), SWAPS AS (
    SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C1
    UNION ALL /* using union all as there can be no duplicates so no need to handle them */
    SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C2
    UNION ALL /* using union all as there can be no duplicates so no need to handle them */
    SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C3
    UNION ALL /* using union all as there can be no duplicates so no need to handle them */
    SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C4
    UNION ALL /* using union all as there can be no duplicates so no need to handle them */
    SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C5
    UNION ALL /* using union all as there can be no duplicates so no need to handle them */
    SELECT base2 AS base_asset, quote2 AS quote_asset, amount2 AS amount, rate2 AS rate, txhash, logindex, time, location FROM C5
    UNION ALL /* using union all as there can be no duplicates so no need to handle them */
    SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C6
    UNION ALL /* using union all as there can be no duplicates so no need to handle them */
    SELECT base2 AS base_asset, quote2 AS quote_asset, amount2 AS amount, rate2 AS rate, txhash, logindex, time, location FROM C6
   )
   SELECT
       txhash + logindex AS id,
       time,
       location,
       base_asset,
       quote_asset,
       'A' AS type, /* always a BUY */
       amount,
       rate,
       NULL AS fee, /* no fee */
       NULL AS fee_currency, /* no fee */
       txhash AS link,
       NULL AS notes /* no notes */
   FROM SWAPS
   UNION ALL /* using union all as there can be no duplicates so no need to handle them */
   SELECT * from trades
;
"""  # noqa: E501

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
{DB_CREATE_ETHEREUM_ACCOUNTS_DETAILS}
{DB_CREATE_MULTISETTINGS}
{DB_CREATE_MANUALLY_TRACKED_BALANCES}
{DB_CREATE_TRADES}
{DB_CREATE_ETHEREUM_TRANSACTIONS}
{DB_CREATE_ETHEREUM_INTERNAL_TRANSACTIONS}
{DB_CREATE_ETHTX_RECEIPTS}
{DB_CREATE_ETHTX_RECEIPT_LOGS}
{DB_CREATE_ETHTX_RECEIPT_LOG_TOPICS}
{DB_CREATE_ETHTX_ADDRESS_MAPPINGS}
{DB_CREATE_MARGIN}
{DB_CREATE_ASSET_MOVEMENTS}
{DB_CREATE_USED_QUERY_RANGES}
{DB_CREATE_EVM_TX_MAPPINGS}
{DB_CREATE_SETTINGS}
{DB_CREATE_TAGS_TABLE}
{DB_CREATE_TAG_MAPPINGS}
{DB_CREATE_AAVE_EVENTS}
{DB_CREATE_YEARN_VAULT_EVENTS}
{DB_CREATE_XPUBS}
{DB_CREATE_XPUB_MAPPINGS}
{DB_CREATE_AMM_SWAPS}
{DB_CREATE_AMM_EVENTS}
{DB_CREATE_ETH2_VALIDATORS}
{DB_CREATE_ETH2_DEPOSITS}
{DB_CREATE_ETH2_DAILY_STAKING_DETAILS}
{DB_CREATE_HISTORY_EVENTS}
{DB_CREATE_HISTORY_EVENTS_MAPPINGS}
{DB_CREATE_ADEX_EVENTS}
{DB_CREATE_LEDGER_ACTION_TYPE}
{DB_CREATE_LEDGER_ACTIONS}
{DB_CREATE_ACTION_TYPE}
{DB_CREATE_IGNORED_ACTIONS}
{DB_CREATE_BALANCER_EVENTS}
{DB_CREATE_NFTS}
{DB_CREATE_COMBINED_TRADES_VIEW}
COMMIT;
PRAGMA foreign_keys=on;
"""
