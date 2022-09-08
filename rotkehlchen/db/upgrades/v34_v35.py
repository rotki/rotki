import json
from typing import TYPE_CHECKING, List, Tuple

from rotkehlchen.constants.resolver import (
    ETHEREUM_DIRECTIVE,
    ETHEREUM_DIRECTIVE_LENGTH,
    ChainID,
    evm_address_to_identifier,
)
from rotkehlchen.db.constants import (
    EVM_ACCOUNTS_DETAILS_LAST_QUERIED_TS,
    EVM_ACCOUNTS_DETAILS_TOKENS,
)
from rotkehlchen.globaldb.upgrades.v2_v3 import OTHER_EVM_CHAINS_ASSETS
from rotkehlchen.types import EvmTokenKind

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor


def _refactor_time_columns(write_cursor: 'DBCursor') -> None:
    """
    The tables that contained time instead of timestamp as column names and need
    to be changed were:
    - timed_balances
    - timed_location_data
    - trades
    - asset_movements
    """
    write_cursor.execute('ALTER TABLE timed_balances RENAME COLUMN time TO timestamp')
    write_cursor.execute('ALTER TABLE timed_location_data RENAME COLUMN time TO timestamp')
    write_cursor.execute('ALTER TABLE trades RENAME COLUMN time TO timestamp')
    write_cursor.execute('ALTER TABLE asset_movements RENAME COLUMN time TO timestamp')


def _create_new_tables(write_cursor: 'DBCursor') -> None:
    write_cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_notes(
        identifier INTEGER NOT NULL PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        location TEXT NOT NULL,
        last_update_timestamp INTEGER NOT NULL,
        is_pinned INTEGER NOT NULL CHECK (is_pinned IN (0, 1))
    );
    """)


def _rename_assets_identifiers(write_cursor: 'DBCursor') -> None:
    """Version 1.26 includes the migration for the global db and the references to assets
    need to be updated also in this database.
    We do an update and relay on the cascade effect to update the assets identifiers in the rest
    of tables.
    """
    write_cursor.execute('SELECT identifier FROM assets')
    old_id_to_new = {}
    for (identifier,) in write_cursor:
        # We only need to update the ethereum assets and those that will be replaced by evm assets
        # Any other asset should keep the identifier they have now.
        if identifier.startswith(ETHEREUM_DIRECTIVE):
            old_id_to_new[identifier] = evm_address_to_identifier(
                address=identifier[ETHEREUM_DIRECTIVE_LENGTH:],
                chain=ChainID.ETHEREUM,
                token_type=EvmTokenKind.ERC20,
            )
        elif identifier in OTHER_EVM_CHAINS_ASSETS:
            old_id_to_new[identifier] = OTHER_EVM_CHAINS_ASSETS[identifier]

    sqlite_tuples = [(new_id, old_id) for old_id, new_id in old_id_to_new.items()]
    write_cursor.executemany('UPDATE assets SET identifier=? WHERE identifier=?', sqlite_tuples)  # noqa: E501


def _change_xpub_mappings_primary_key(write_cursor: 'DBCursor', conn: 'DBConnection') -> None:
    """This upgrade includes xpub_mappings' `blockchain` column in primary key.
    After this upgrade it will become possible to create mapping for the same bitcoin address
    and xpub on different blockchains.

    Despite `blockchain` was not previously in the primary key, data in this table should not
    be broken since it has FOREIGN KEY (which includes `blockchain`) referencing xpubs table.
    """
    with conn.read_ctx() as read_cursor:
        xpub_mappings = read_cursor.execute('SELECT * from xpub_mappings').fetchall()
    write_cursor.execute("""CREATE TABLE xpub_mappings_copy (
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
    """)
    write_cursor.executemany('INSERT INTO xpub_mappings_copy VALUES (?, ?, ?, ?, ?, ?)', xpub_mappings)  # noqa: E501
    write_cursor.execute('DROP TABLE xpub_mappings')
    write_cursor.execute('ALTER TABLE xpub_mappings_copy RENAME TO xpub_mappings')


def _clean_amm_swaps(cursor: 'DBCursor') -> None:
    """Since we remove the amm swaps, clean all related DB tables and entries"""
    cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "uniswap_trades%";')
    cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "sushiswap_trades%";')
    cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "balancer_trades%";')
    cursor.execute('DROP VIEW IF EXISTS combined_trades_view;')
    cursor.execute('DROP TABLE IF EXISTS amm_swaps;')


def _add_blockchain_column_web3_nodes(cursor: 'DBCursor') -> None:
    cursor.execute('ALTER TABLE web3_nodes RENAME TO web3_nodes_old')
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS web3_nodes(
        identifier INTEGER NOT NULL PRIMARY KEY,
        name TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        owned INTEGER NOT NULL CHECK (owned IN (0, 1)),
        active INTEGER NOT NULL CHECK (active IN (0, 1)),
        weight INTEGER NOT NULL,
        blockchain TEXT NOT NULL
    );
    """)
    cursor.execute("INSERT INTO web3_nodes SELECT identifier, name, endpoint, owned, active, weight, 'ETH' FROM web3_nodes_old")  # noqa: E501
    cursor.execute('DROP TABLE web3_nodes_old')


def _update_ignored_assets_identifiers_to_caip_format(cursor: 'DBCursor') -> None:
    cursor.execute('SELECT value FROM multisettings WHERE name="ignored_asset";')
    old_ids_to_caip_ids_mappings: List[Tuple[str, str]] = []
    for (old_identifier,) in cursor:
        if old_identifier is not None and old_identifier.startswith(ETHEREUM_DIRECTIVE):
            old_ids_to_caip_ids_mappings.append(
                (
                    evm_address_to_identifier(
                        address=old_identifier[ETHEREUM_DIRECTIVE_LENGTH:],
                        chain=ChainID.ETHEREUM,
                        token_type=EvmTokenKind.ERC20,
                    ),
                    old_identifier,
                ),
            )

    cursor.executemany(
        'UPDATE multisettings SET value=? WHERE value=? AND name="ignored_asset"',
        old_ids_to_caip_ids_mappings,
    )


def _rename_assets_in_user_queried_tokens(cursor: 'DBCursor') -> None:
    """ethereum_accounts_details has the column tokens_list as a json list with identifiers
    using the _ceth_ format. Those need to be upgraded to the CAIPS format.
    The approach we took was to refactor this table adding a key-value table with the chain
    attribute to map properties of accounts to differt chains
    """
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evm_accounts_details (
        account VARCHAR[42] NOT NULL,
        chain CHAR(1) NOT NULL DEFAULT('A'),
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        PRIMARY KEY (account, chain, key, value)
    );
    """)
    cursor.execute('SELECT account, tokens_list, time FROM ethereum_accounts_details')
    update_rows = []
    for address, token_list, timestamp in cursor:
        tokens = json.loads(token_list)
        for token in tokens.get('tokens', []):
            new_id = evm_address_to_identifier(
                address=token[ETHEREUM_DIRECTIVE_LENGTH:],
                chain=ChainID.ETHEREUM,
                token_type=EvmTokenKind.ERC20,
            )
            update_rows.append(
                (
                    address,
                    ChainID.ETHEREUM.serialize_for_db(),
                    EVM_ACCOUNTS_DETAILS_TOKENS,
                    new_id,
                ),
            )
        update_rows.append(
            (
                address,
                ChainID.ETHEREUM.serialize_for_db(),
                EVM_ACCOUNTS_DETAILS_LAST_QUERIED_TS,
                timestamp,
            ),
        )
    cursor.executemany(
        'INSERT OR IGNORE INTO evm_accounts_details(account, chain, key, value) VALUES(?, ?, ?, ?);',  # noqa: E501
        update_rows,
    )
    cursor.execute('DROP TABLE ethereum_accounts_details')


def upgrade_v34_to_v35(db: 'DBHandler') -> None:
    """Upgrades the DB from v34 to v35
    - Change tables where time is used as column name to timestamp
    - Add user_notes table
    - Renames the asset identifiers to use CAIPS
    """
    with db.user_write() as write_cursor:
        _rename_assets_identifiers(write_cursor)
        _update_ignored_assets_identifiers_to_caip_format(write_cursor)
        _refactor_time_columns(write_cursor)
        _clean_amm_swaps(write_cursor)
        _create_new_tables(write_cursor)
        _change_xpub_mappings_primary_key(write_cursor=write_cursor, conn=db.conn)
        _add_blockchain_column_web3_nodes(write_cursor)
        _create_new_tables(write_cursor)
        _rename_assets_in_user_queried_tokens(write_cursor)
