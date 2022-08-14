import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants.resolver import (
    ETHEREUM_DIRECTIVE,
    ETHEREUM_DIRECTIVE_LENGTH,
    ChainID,
    EvmTokenKind,
    evm_address_to_identifier,
    strethaddress_to_identifier,
)

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor

log = logging.getLogger(__name__)

OTHER_EVM_CHAINS_ASSETS = {
    'SHA',
    'WRX',
    'BAN',
    'WXT',
    'ROCO',
    'NHCT',
    'VOXEL',
    'FEVR',
    'BIFI',
    'GBYTE',
    'BLOK',
    'IDIA',
    'POLYDOGE',
    'JOE',
    'IQ',
    'ANY',
    'EWT',
    'UPO',
    'H3RO3S',
    'UBQ',
    'XAVA',
    'FLAME',
    'OP',
    'PLATO',
    'USDN',
    'TIME',
    'MV',
    'COVAL',
    'KLIMA',
    'POT',
    'FITFI',
    'PNG',
    'DINO',
    'GAME',
    'AVAX',
    'ETHO',
    'POLX',
    'QI',
}
COMMON_ASSETS_INSERT = """INSERT OR IGNORE INTO common_asset_details(
    identifier, name, symbol, coingecko, cryptocompare, forked
    ) VALUES(?, ?, ?, ?, ?, ?)
"""
ASSETS_INSERT = """INSERT OR IGNORE INTO assets(
        identifier, type, started, swapped_for
    )VALUES(?, ?, ?, ?);
"""
EVM_TOKEN_INSERT = """INSERT OR IGNORE INTO evm_tokens(
        identifier, token_kind, chain, address, decimals, protocol
    ) VALUES(?, ?, ?, ?, ?, ?)
"""
UNDERLYING_TOKEN_INSERT = """INSERT OR IGNORE INTO
    underlying_tokens_list(identifier, weight, parent_token_entry)
    VALUES (?, ?, ?)
"""
OWNED_ASSETS_INSERT = 'INSERT OR IGNORE INTO user_owned_assets(asset_id) VALUES (?);'
PRICES_INSERT = 'INSERT INTO price_history(from_asset, to_asset, source_type, timestamp, price) VALUES (?, ?, ?, ?, ?)'  # noqa: E501


EVM_TUPLES_CREATION_TYPE = (
    Tuple[
        List[Tuple[str, str, str, str, Any, Any]],
        List[Tuple[Any, str, Any, Optional[str]]],
        List[Tuple[Any, Any, Any, Any, Any, None]],
    ]
)

ASSET_CREATION_TYPE = (
    Tuple[
        List[Tuple[Any, Any, Any, Any]],
        List[Tuple[Any, Any, Any, Any, Any, Any]],
    ]
)


def upgrade_ethereum_assets(query: List[Any]) -> EVM_TUPLES_CREATION_TYPE:
    old_ethereum_data = []
    old_ethereum_id_to_new = {}
    evm_tuples = []
    assets_tuple = []
    common_asset_details = []

    for entry in query:
        new_id = evm_address_to_identifier(
            address=entry[0],
            chain=ChainID.ETHEREUM,
            token_type=EvmTokenKind.ERC20,
            collectible_id=None,
        )
        old_ethereum_id_to_new[entry[3]] = new_id
        old_ethereum_data.append((new_id, *entry))

    for entry in old_ethereum_data:
        evm_tuples.append((
            str(entry[0]),  # identifier
            EvmTokenKind.ERC20.serialize_for_db(),  # token type
            ChainID.ETHEREUM.serialize_for_db(),  # chain
            str(entry[1]),  # address
            entry[2],  # decimals
            entry[3],  # protocol
        ))
        new_swapped_for = old_ethereum_id_to_new.get(entry[8])
        if new_swapped_for is not None:
            new_swapped_for = evm_address_to_identifier(
                address=entry[8][ETHEREUM_DIRECTIVE_LENGTH:],
                chain=ChainID.ETHEREUM,
                token_type=EvmTokenKind.ERC20,
            )
            old_ethereum_id_to_new[entry[8]] = new_swapped_for

        assets_tuple.append((
            entry[0],  # identifier
            AssetType.EVM_TOKEN.serialize_for_db(),  # type
            entry[7],  # started
            new_swapped_for,  # swapped for
        ))
        common_asset_details.append((
            entry[0],  # identifier
            entry[5],  # name
            entry[6],  # symbol
            entry[9],  # coingecko
            entry[10],  # cryptocompare
            None,  # forked, none for eth
        ))

    return (
        evm_tuples,
        assets_tuple,
        common_asset_details,
    )


def upgrade_ethereum_asset_ids_v3(cursor: 'DBCursor') -> EVM_TUPLES_CREATION_TYPE:
    """Query all the information available from ethereum tokens in
    the v2 schema to be used in v3"""
    result = cursor.execute(
        'SELECT A.address, A.decimals, A.protocol, B.identifier, B.name, B.symbol, B.started, '
        'B.swapped_for, B.coingecko, B.cryptocompare FROM assets '
        'AS B JOIN ethereum_tokens '
        'AS A ON A.address = B.details_reference WHERE B.type="C";',
    )  # noqa: E501

    return upgrade_ethereum_assets(result.fetchall())


def upgrade_other_assets(cursor: 'DBCursor') -> ASSET_CREATION_TYPE:
    """Create the bindings typle for the assets and common_asset_details tables using the
    information from the V2 tables for non ethereum assets"""
    chains = ",".join([f'"{x}"' for x in ('C',)])
    result = cursor.execute(
        f'SELECT A.identifier, A.type, A.name, A.symbol, A.started, A.swapped_for, A.coingecko, '
        f'A.cryptocompare, B.forked FROM assets as A JOIN common_asset_details AS B '
        f'ON B.asset_id=A.identifier WHERE A.type NOT IN ({chains})',
    )  # noqa: E501

    assets_tuple = []
    common_asset_details = []
    for entry in result:
        if entry[0] in OTHER_EVM_CHAINS_ASSETS:
            continue
        assets_tuple.append((
            entry[0],  # identifier
            entry[1],  # type
            entry[4],  # started
            entry[5],  # swapped for
        ))
        common_asset_details.append((
            entry[0],  # identifier
            entry[2],  # name
            entry[3],  # symbol
            entry[6],  # coingecko
            entry[7],  # cryptocompare
            entry[8],  # forked
        ))

    return (
        assets_tuple,
        common_asset_details,
    )


def translate_underlying_table(cursor: 'DBCursor') -> List[Tuple[str, str, str]]:
    """Get information about the underlying tokens and upgrade it to the V3 schema from the
    information in the v2 schema"""
    query = cursor.execute(
        'SELECT address, weight, parent_token_entry FROM underlying_tokens_list;',
    )
    mappings = []
    for row in query:
        new_address = evm_address_to_identifier(
            address=row[0],
            chain=ChainID.ETHEREUM,
            token_type=EvmTokenKind.ERC20,
            collectible_id=None,
        )
        new_parent = evm_address_to_identifier(
            address=row[2],
            chain=ChainID.ETHEREUM,
            token_type=EvmTokenKind.ERC20,
            collectible_id=None,
        )
        mappings.append((new_address, row[1], new_parent))
    return mappings


def translate_owned_assets(cursor: 'DBCursor') -> List[Tuple[str]]:
    """Collect and update assets in the user_owned_assets tables to use the new id format"""
    cursor.execute('SELECT asset_id from user_owned_assets;')
    owned_assets = []
    for (asset_id,) in cursor:
        new_id = asset_id
        if asset_id.startswith(ETHEREUM_DIRECTIVE):
            new_id = strethaddress_to_identifier(asset_id[ETHEREUM_DIRECTIVE_LENGTH:])
        owned_assets.append((new_id,))
    return owned_assets


def translate_assets_in_price_table(cursor: 'DBCursor') -> List[Tuple[str, str, str, int, str]]:
    cursor.execute(
        'SELECT from_asset, to_asset, source_type, timestamp, price FROM price_history',
    )
    updated_rows = []
    for (from_asset, to_asset, source_type, timestamp, price) in cursor:
        new_from_asset, new_to_asset = from_asset, to_asset
        if new_from_asset.startswith(ETHEREUM_DIRECTIVE):
            new_from_asset = strethaddress_to_identifier(new_from_asset[ETHEREUM_DIRECTIVE_LENGTH:])  # noqa: E501
        if new_to_asset.startswith(ETHEREUM_DIRECTIVE):
            new_to_asset = strethaddress_to_identifier(new_to_asset[ETHEREUM_DIRECTIVE_LENGTH:])
        updated_rows.append((new_from_asset, new_to_asset, source_type, timestamp, price))

    return updated_rows


def migrate_to_v3(connection: 'DBConnection') -> None:
    """Upgrade assets information and migrate globaldb to version 3"""

    with connection.read_ctx() as cursor:
        # Obtain information for ethereum assets
        evm_tuples, assets_tuple, common_asset_details = upgrade_ethereum_asset_ids_v3(cursor)
        # Underlying tokens mappings
        mappings = translate_underlying_table(cursor)
        assets_tuple_others, common_asset_details_others = upgrade_other_assets(cursor)
        owned_assets = translate_owned_assets(cursor)
        updated_prices = translate_assets_in_price_table(cursor)

    with connection.write_ctx() as cursor:
        # Purge or delete tables with outdated information
        cursor.executescript("""
        PRAGMA foreign_keys=off;
        DROP TABLE IF EXISTS user_owned_assets;
        DROP TABLE IF EXISTS assets;
        DROP TABLE IF EXISTS ethereum_tokens;
        DROP TABLE IF EXISTS evm_tokens;
        DROP TABLE IF EXISTS common_asset_details;
        DROP TABLE IF EXISTS underlying_tokens_list;
        DROP TABLE IF EXISTS price_history;
        PRAGMA foreign_keys=on;
        """)

        # Create new tables
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS common_asset_details(
            identifier TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
            name TEXT,
            symbol TEXT,
            coingecko TEXT,
            cryptocompare TEXT,
            forked TEXT,
            FOREIGN KEY(forked) REFERENCES assets(identifier) ON UPDATE CASCADE
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            identifier TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
            type CHAR(1) NOT NULL DEFAULT('A') REFERENCES asset_types(type),
            started INTEGER,
            swapped_for TEXT,
            FOREIGN KEY(swapped_for) REFERENCES assets(identifier) ON UPDATE CASCADE
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS evm_tokens (
            identifier TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
            token_kind CHAR(1) NOT NULL DEFAULT('A') REFERENCES token_kinds(token_kind),
            chain CHAR(1) NOT NULL DEFAULT('A') REFERENCES chain_ids(chain),
            address VARCHAR[42] NOT NULL,
            decimals INTEGER,
            protocol TEXT
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS multiasset_collector(
            identifier TEXT NOT NULL,
            child_asset_id TEXT,
            FOREIGN KEY(child_asset_id) REFERENCES assets(identifier) ON UPDATE CASCADE
            FOREIGN KEY(identifier) REFERENCES assets(identifier) ON UPDATE CASCADE
            PRIMARY KEY(identifier, child_asset_id)
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_owned_assets (
            asset_id VARCHAR[24] NOT NULL PRIMARY KEY,
            FOREIGN KEY(asset_id) REFERENCES assets(identifier) ON UPDATE CASCADE
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS underlying_tokens_list (
            identifier TEXT NOT NULL,
            weight TEXT NOT NULL,
            parent_token_entry TEXT NOT NULL,
            FOREIGN KEY(parent_token_entry) REFERENCES evm_tokens(identifier)
                ON DELETE CASCADE ON UPDATE CASCADE
            FOREIGN KEY(identifier) REFERENCES evm_tokens(identifier) ON UPDATE CASCADE
            PRIMARY KEY(identifier, parent_token_entry)
        );
        """)
        cursor.execute("""
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
        """)  # noqa: E501
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS asset_collection_properties(
            identifier TEXT NOT NULL PRIMARY KEY,
            name TEXT NOT NULL,
            symbol TEXT NOT NULL,
            FOREIGN KEY(identifier) REFERENCES multiasset_collector(identifier) ON UPDATE CASCADE ON DELETE CASCADE
        );
        """)  # noqa: E501
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_asset(
            identifier INTEGER NOT NULL PRIMARY KEY,
            name TEXT NOT NULL,
            symbol TEXT,
            notes TEXT,
            asset_type TEXT
        );
        """)

        cursor.executescript('PRAGMA foreign_keys=off;')
        cursor.executemany(COMMON_ASSETS_INSERT, common_asset_details)
        cursor.executemany(COMMON_ASSETS_INSERT, common_asset_details_others)
        cursor.executemany(ASSETS_INSERT, assets_tuple)
        cursor.executemany(ASSETS_INSERT, assets_tuple_others)
        cursor.executemany(OWNED_ASSETS_INSERT, owned_assets)
        cursor.executemany(PRICES_INSERT, updated_prices)
        cursor.executescript('PRAGMA foreign_keys=on;')
        cursor.executemany(EVM_TOKEN_INSERT, evm_tuples)
        cursor.executemany(UNDERLYING_TOKEN_INSERT, mappings)

        dir_path = Path(__file__).resolve().parent.parent.parent
        with open(dir_path / 'data' / 'globaldb_v2_v3_assets.sql', 'r') as f:
            sql_sentences = f.read()
            cursor.executescript(sql_sentences)
        connection.commit()
