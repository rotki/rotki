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
    coingecko TEXT,
    cryptocompare TEXT
);
"""

DB_CREATE_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    name VARCHAR[24] NOT NULL PRIMARY KEY,
    value TEXT
);
"""

DB_SCRIPT_CREATE_TABLES = """
PRAGMA foreign_keys=off;
BEGIN TRANSACTION;
{}{}{}
COMMIT;
PRAGMA foreign_keys=on;
""".format(
    DB_CREATE_ETHEREUM_TOKENS,
    DB_CREATE_ETHEREUM_TOKENS_LIST,
    DB_CREATE_SETTINGS,
)
