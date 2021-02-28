DB_CREATE_ETHEREUM_TOKENS = """
CREATE TABLE IF NOT EXISTS ethereum_tokens (
    address VARCHAR[42] PRIMARY KEY NOT NULL,
    decimals INTEGER NOT NULL,
    name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    started INTEGER,
    coingecko TEXT,
    cryptocompare TEXT,
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
{}{}
COMMIT;
PRAGMA foreign_keys=on;
""".format(
    DB_CREATE_ETHEREUM_TOKENS,
    DB_CREATE_SETTINGS,
)
