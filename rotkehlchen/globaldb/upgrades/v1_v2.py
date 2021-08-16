import logging
import sqlite3
from collections import defaultdict

from rotkehlchen.constants.resolver import ETHEREUM_DIRECTIVE
from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


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
    ethereum_details_tuples = []

    # run through all entries first to populate old_ethereum_id_to_new
    for entry in result:
        new_id = ETHEREUM_DIRECTIVE + entry[1]
        old_ethereum_id_to_new[entry[0]] = new_id
        old_ethereum_data.append((new_id, *entry[1:]))

    for entry in old_ethereum_data:
        new_swapped_for = old_ethereum_id_to_new.get(entry[6], entry[6])
        ethereum_asset_tuples.append((
            entry[0],  # identifier
            'C',  # type
            entry[3],  # name
            entry[4],  # symbol
            entry[5],  # started
            new_swapped_for,
            entry[7],  # coingecko
            entry[8],  # cryptocompare
            entry[1],  # details reference
        ))
        ethereum_details_tuples.append((
            entry[1],  # address
            entry[2],  # decimals
            entry[9],  # protocol
        ))

    result = cursor.execute(
        'SELECT A.identifier, A.type, B.name, B.symbol, B.started, B.forked, '
        'B.swapped_for, B.coingecko, B.cryptocompare FROM assets '
        'AS A LEFT OUTER JOIN common_asset_details '
        'as B ON B.asset_id = A.identifier WHERE A.type!="C";',
    )
    other_assets_tuples = []
    other_assets_details_tuples = []
    for entry in result:
        new_forked = old_ethereum_id_to_new.get(entry[5], entry[5])
        new_swapped_for = old_ethereum_id_to_new.get(entry[6], entry[6])
        other_assets_tuples.append((
            entry[0],  # identifier
            entry[1],  # type
            entry[2],  # name
            entry[3],  # symbol
            entry[4],  # started
            new_swapped_for,
            entry[7],  # coingecko
            entry[8],  # cryptocompare
            entry[0],  # details reference
        ))
        other_assets_details_tuples.append((
            entry[0],  # asset_id
            new_forked,
        ))
    result = cursor.execute('SELECT asset_id from user_owned_assets;')
    owned_assets_tuples = result.fetchall()

    # Delete all tables that are gonna get modified and get new data
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
        name TEXT,
        symbol TEXT,
        started INTEGER,
        swapped_for TEXT,
        coingecko TEXT,
        cryptocompare TEXT,
        details_reference TEXT,
        FOREIGN KEY(swapped_for) REFERENCES assets(identifier) ON UPDATE CASCADE
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ethereum_tokens (
        address VARCHAR[42] PRIMARY KEY NOT NULL,
        decimals INTEGER,
        protocol TEXT
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
        PRIMARY KEY(address, parent_token_entry)
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS common_asset_details (
        asset_id TEXT PRIMARY KEY NOT NULL,
        forked STRING,
        FOREIGN KEY(asset_id) REFERENCES assets(identifier) ON DELETE CASCADE ON UPDATE CASCADE,
        FOREIGN KEY(forked) REFERENCES assets(identifier) ON UPDATE CASCADE
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_owned_assets (
    asset_id VARCHAR[24] NOT NULL PRIMARY KEY,
    FOREIGN KEY(asset_id) REFERENCES assets(identifier) ON UPDATE CASCADE
    );
    """)

    # and now let's put the data back starting with the assets and ethereum tokens tables
    ordered_asset_tuples = []
    entries_with_unknown_swapped_for = defaultdict(list)
    processed_identifiers = set()
    for entry in ethereum_asset_tuples + other_assets_tuples:
        entry_id = entry[0]
        swapped_for = entry[5]
        if swapped_for is not None and swapped_for not in processed_identifiers:
            # has unknown dependencies, let's wait
            entries_with_unknown_swapped_for[swapped_for].append(entry)
            continue

        # else just add the entry
        ordered_asset_tuples.append(entry)
        processed_identifiers.add(entry_id)
        # also check if this entry is a missing swapped for. If yes add dependencies
        dependencies = entries_with_unknown_swapped_for.get(entry_id)
        if dependencies is not None:
            for dependency in dependencies:
                ordered_asset_tuples.append(dependency)
                processed_identifiers.add(dependency[0])
            entries_with_unknown_swapped_for.pop(entry_id)

    # if we have any assets with unknown dependencies left that's a problem. Note it as error
    # Can't do msg_aggregator here since we don't have it yet
    # TODO: Think of a solution for this. Is probably possible and would be useful
    for swapped_for_id, entries_list in entries_with_unknown_swapped_for.items():
        for entry in entries_list:
            log.error(
                f'During GlobalDB upgrade v1->v2 could not find asset with identifier '
                f'{swapped_for_id} so asset with identifier {entry[0]} that depended on'
                f' it for swapped_for gets an empty value there',
            )
            modified_tuple = list(entry)
            modified_tuple[5] = None
            ordered_asset_tuples.append(tuple(modified_tuple))

    cursor.executemany(
        """INSERT OR IGNORE INTO assets(
            identifier, type, name, symbol, started, swapped_for,
            coingecko, cryptocompare, details_reference
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ordered_asset_tuples,
    )

    cursor.executemany(
        """INSERT OR IGNORE INTO ethereum_tokens(address, decimals, protocol) VALUES(?, ?, ?);""",
        ethereum_details_tuples,
    )
    cursor.executemany(
        """INSERT OR IGNORE INTO underlying_tokens_list(address, weight,
        parent_token_entry) VALUES (?, ?, ?);""",
        underlying_tokens_list_tuples,
    )
    # all other asset details
    cursor.executemany(
        """INSERT OR IGNORE INTO common_asset_details(asset_id, forked) VALUES(?, ?)""",
        other_assets_details_tuples,
    )
    # and finally the user owned assets table
    cursor.executemany(
        'INSERT OR IGNORE INTO user_owned_assets(asset_id) VALUES(?)',
        owned_assets_tuples,
    )
    connection.commit()
