import sqlite3

from rotkehlchen.constants.resolver import ETHEREUM_DIRECTIVE


def upgrade_ethereum_asset_ids(connection: sqlite3.Connection) -> None:
    # Get all old data from the DB
    cursor = connection.cursor()
    result = cursor.execute('SELECT * from underlying_tokens_list;')
    underlying_tokens_list_tuples = result.fetchall()
    result = cursor.execute(
        'SELECT A.identifier, B.address, B.decimals, B.name, B.symbol, B.started, '
        'B.swapped_for, B.coingecko, B.cryptocompare, B.protocol FROM assets '
        'AS A LEFT OUTER JOIN ethereum_tokens '
        'as B ON B.address = A.details_reference WHERE A.type="C";',
    )
    old_ethereum_data = []
    old_ethereum_id_to_new = {}
    ethereum_asset_tuples = []
    for entry in result:
        old_ethereum_data.append(list(entry)[1:])
        new_id = ETHEREUM_DIRECTIVE + entry[1]
        old_ethereum_id_to_new[entry[0]] = new_id
        ethereum_asset_tuples.append((new_id, 'C', entry[1]))

    result = cursor.execute(
        'SELECT A.identifier, A.type, B.name, B.symbol, B.started, B.forked, '
        'B.swapped_for, B.coingecko, B.cryptocompare FROM assets '
        'AS A LEFT OUTER JOIN common_asset_details '
        'as B ON B.asset_id = A.identifier WHERE A.type!="C";',
    )
    other_assets_tuples = []
    other_assets_details_tuples = []
    for entry in result:
        other_assets_tuples.append((entry[0], entry[1], entry[0]))
        new_forked = old_ethereum_id_to_new.get(entry[5], entry[5])
        new_swapped_for = old_ethereum_id_to_new.get(entry[6], entry[6])
        other_assets_details_tuples.append((
            entry[0],
            entry[2],
            entry[3],
            entry[4],
            new_forked,
            new_swapped_for,
            entry[7],
            entry[8],
        ))
    result = cursor.execute('SELECT asset_id from user_owned_assets;')
    owned_assets_tuples = result.fetchall()

    # Delete all tables that aregonna get modified and get new data
    cursor.executescript("""
    PRAGMA foreign_keys=off;
    DROP TABLE IF EXISTS owned_assets;
    DROP TABLE IF EXISTS assets;
    DROP TABLE IF EXISTS ethereum_tokens;
    DROP TABLE IF EXISTS common_asset_details;
    DROP TABLE IF EXISTS underlying_tokens_list;
    PRAGMA foreign_keys=on;
    """)

    # Recreate the tables with the foreign keys cascading on update
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assets (
    identifier TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
    type CHAR(1) NOT NULL DEFAULT('A') REFERENCES asset_types(type),
    details_reference TEXT);
    """)
    cursor.execute("""
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
    FOREIGN KEY(swapped_for) REFERENCES assets(identifier) ON UPDATE CASCADE
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS underlying_tokens_list (
    address VARCHAR[42] NOT NULL,
    weight TEXT NOT NULL,
    parent_token_entry TEXT NOT NULL,
    FOREIGN KEY(parent_token_entry) REFERENCES ethereum_tokens(address)
        ON DELETE CASCADE ON UPDATE CASCADE
    FOREIGN KEY(address) REFERENCES ethereum_tokens(address) ON UPDATE CASCADE
    PRIMARY KEY(address, parent_token_entry));
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS common_asset_details (
    asset_id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    symbol TEXT,
    started INTEGER,
    forked STRING,
    swapped_for STRING,
    coingecko TEXT,
    cryptocompare TEXT,
    FOREIGN KEY(asset_id) REFERENCES assets(identifier) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY(swapped_for) REFERENCES assets(identifier) ON UPDATE CASCADE,
    FOREIGN KEY(forked) REFERENCES assets(identifier) ON UPDATE CASCADE
    );""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_owned_assets (
    asset_id VARCHAR[24] NOT NULL PRIMARY KEY,
    FOREIGN KEY(asset_id) REFERENCES assets(identifier) ON UPDATE CASCADE
    );
    """)

    # and now let's put the data back starting with the assets and ethereum tokens tables
    cursor.executemany(
        """INSERT OR IGNORE INTO assets(identifier, type, details_reference)
        VALUES(?, ?, ?)""",
        other_assets_tuples,
    )
    cursor.executemany(
        """INSERT OR IGNORE INTO assets(identifier, type, details_reference)
        VALUES(?, ?, ?)""",
        ethereum_asset_tuples,
    )
    ethereum_tokens_tuples = []
    for entry in old_ethereum_data:
        new_swapped_for = old_ethereum_id_to_new.get(entry[5], entry[5])
        entry[5] = new_swapped_for
        ethereum_tokens_tuples.append(tuple(entry))
    cursor.executemany(
        """INSERT OR IGNORE INTO ethereum_tokens(address, decimals, name, symbol, started,
        swapped_for, coingecko, cryptocompare, protocol) VALUES(?, ?, ?, ?, ?, ?, ?, ? ,?)""",
        ethereum_tokens_tuples,
    )
    cursor.executemany(
        """INSERT OR IGNORE INTO underlying_tokens_list(address, weight,
        parent_token_entry) VALUES (?, ?, ?);""",
        underlying_tokens_list_tuples,
    )
    # all other asset details
    cursor.executemany(
        """INSERT OR IGNORE INTO common_asset_details(asset_id, name, symbol, started,
        forked, swapped_for, coingecko, cryptocompare) VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
        other_assets_details_tuples,
    )
    # and finally the user owned assets table
    cursor.executemany(
        'INSERT OR IGNORE INTO user_owned_assets(asset_id) VALUES(?)',
        owned_assets_tuples,
    )

    connection.commit()
