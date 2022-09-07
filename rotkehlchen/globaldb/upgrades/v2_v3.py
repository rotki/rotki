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
    'WAL',
    'EPX',
    'H2O',
    'GSPI',
    'PORTO',
    'KLIMA',
    'OP',
    'ERTHA',
    'BLOK',
    'SIN',
    'JOE',
    'MDX',
    'AUSD',
    'DAR',
    'BRISE',
    'TIME',
    'RD',
    'SMG',
    'ROSN',
    'LAZIO',
    'BURGER',
    'SSG',
    'XVS',
    'QI',
    'H3RO3S',
    'ELV',
    'NFTB',
    'DREAMS',
    'SFP',
    'BIFI',
    'BSW',
    'TKO',
    'CATE',
    'ARV',
    'MNST',
    'CAKE',
    'KARA',
    'DLTA',
    'SPARTA',
    'VAI',
    'FLAME',
    'LACE',
    'UPO',
    'CRFI',
    'HERO',
    'RACA',
    'TWT',
    'CHMB',
    'NRV',
    'bDOT',
    'WOOP',
    'PLGR',
    'GODZ',
    'MV',
    'LAVAX',
    'SURV',
    'PNG',
    'SFUND',
    'DINO',
    'GMM',
    'OPS',
    'WSB',
    'YEFI',
    'SCLP',
    'SON',
    'REV3L',
    'IDIA',
    'MONI',
    'PLATO',
    'VOXEL',
    'BMON',
    'SANTOS',
    'ANI',
    'ZPTC',
    'POSI',
    'GGG',
    'NBT',
    'MQST',
    'MTRG',
    'EPS',
    'FALCONS',
    'LATTE',
    'GAFI',
    'FEVR',
    'ALPACA',
    'BNX',
    'IHC',
    'ETHO',
    'STARLY',
    'ITAMCUBE',
    'CHESS',
    'NHCT',
    'TAUM',
    'FITFI',
    'XEP',
    'ALPINE',
    'SWINGBY',
    'POLYDOGE',
    'ROCO',
    'DPET',
    'ARKER',
    'MBOX',
    'XWG',
    'XAVA',
    'BAKE',
    'WRX',
}
COMMON_ASSETS_INSERT = """INSERT OR IGNORE INTO common_asset_details(
    identifier, symbol, coingecko, cryptocompare, forked
    ) VALUES(?, ?, ?, ?, ?)
"""
ASSETS_INSERT = """INSERT OR IGNORE INTO assets(
        identifier, name, type, started, swapped_for
    )VALUES(?, ?, ?, ?, ?);
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
BINANCE_INSERT = 'INSERT INTO binance_pairs(pair, base_asset, quote_asset, location) VALUES(?, ?, ?, ?)'  # noqa: E501


EVM_TUPLES_CREATION_TYPE = (
    Tuple[
        List[Tuple[str, str, str, str, Any, Any]],
        List[Tuple[Any, Any, str, Any, Optional[str]]],
        List[Tuple[Any, Any, Any, Any, None]],
    ]
)

ASSET_CREATION_TYPE = (
    Tuple[
        List[Tuple[Any, Any, Any, Any, Any]],
        List[Tuple[Any, Any, Any, Any, Any]],
    ]
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
    query = result.fetchall()
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
            entry[5],  # name
            AssetType.EVM_TOKEN.serialize_for_db(),  # type
            entry[7],  # started
            new_swapped_for,  # swapped for
        ))
        common_asset_details.append((
            entry[0],  # identifier
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


def upgrade_other_assets(cursor: 'DBCursor') -> ASSET_CREATION_TYPE:
    """Create the bindings tuple for the assets and common_asset_details tables using the
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
        swapped_for = entry[5]
        if swapped_for is not None and swapped_for.startswith(ETHEREUM_DIRECTIVE):
            swapped_for = evm_address_to_identifier(
                address=swapped_for[ETHEREUM_DIRECTIVE_LENGTH:],
                chain=ChainID.ETHEREUM,
                token_type=EvmTokenKind.ERC20,
            )
        assets_tuple.append((
            entry[0],  # identifier
            entry[2],  # name
            entry[1],  # type
            entry[4],  # started
            swapped_for,
        ))
        common_asset_details.append((
            entry[0],  # identifier
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


def translate_binance_pairs(cursor: 'DBCursor') -> List[Tuple[str, str, str, str]]:
    """Collect and update assets in the binance_pairs tables to use the new id format"""
    cursor.execute('SELECT pair, base_asset, quote_asset, location from binance_pairs;')
    binance_pairs = []
    for entry in cursor:
        new_base = entry[1]
        if new_base.startswith(ETHEREUM_DIRECTIVE):
            new_base = strethaddress_to_identifier(new_base[ETHEREUM_DIRECTIVE_LENGTH:])
        new_quote = entry[2]
        if new_quote.startswith(ETHEREUM_DIRECTIVE):
            new_quote = strethaddress_to_identifier(new_quote[ETHEREUM_DIRECTIVE_LENGTH:])
        binance_pairs.append((entry[0], new_base, new_quote, entry[3]))

    return binance_pairs


def translate_assets_in_price_table(cursor: 'DBCursor') -> List[Tuple[str, str, str, int, str]]:
    """
    Translate the asset ids in the price table.

    Also drop all non manually input asset prices since otherwise this upgrade
    will take forever. A heavily used globaldb
    """
    # cursor.execute('DELETE from price_history WHERE source_type!="A"')
    cursor.execute(
        'SELECT from_asset, to_asset, source_type, timestamp, price FROM '
        'price_history WHERE source_type=="A"',
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
        updated_binance_pairs = translate_binance_pairs(cursor)

    with connection.write_ctx() as cursor:
        # Purge or delete tables with outdated information. Some of these tables
        # like user_owned_assets are recreated in an identical state but are dropped
        # and recreated since they have references to a table that is dropped and modified
        cursor.executescript("""
        PRAGMA foreign_keys=off;
        DROP TABLE IF EXISTS user_owned_assets;
        DROP TABLE IF EXISTS assets;
        DROP TABLE IF EXISTS ethereum_tokens;
        DROP TABLE IF EXISTS evm_tokens;
        DROP TABLE IF EXISTS common_asset_details;
        DROP TABLE IF EXISTS underlying_tokens_list;
        DROP TABLE IF EXISTS price_history;
        DROP TABLE IF EXISTS binance_pairs;
        PRAGMA foreign_keys=on;
        """)

        # Create new tables
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS chain_ids (
          chain    CHAR(1)       PRIMARY KEY NOT NULL,
          seq     INTEGER UNIQUE
        );
        /* ETHEREUM */
        INSERT OR IGNORE INTO chain_ids(chain, seq) VALUES ('A', 1);
        /* OPTIMISM */
        INSERT OR IGNORE INTO chain_ids(chain, seq) VALUES ('B', 2);
        /* BINANCE */
        INSERT OR IGNORE INTO chain_ids(chain, seq) VALUES ('C', 3);
        /* GNOSIS */
        INSERT OR IGNORE INTO chain_ids(chain, seq) VALUES ('D', 4);
        /* MATIC */
        INSERT OR IGNORE INTO chain_ids(chain, seq) VALUES ('E', 5);
        /* FANTOM */
        INSERT OR IGNORE INTO chain_ids(chain, seq) VALUES ('F', 6);
        /* ARBITRUM */
        INSERT OR IGNORE INTO chain_ids(chain, seq) VALUES ('G', 7);
        /* AVALANCHE */
        INSERT OR IGNORE INTO chain_ids(chain, seq) VALUES ('H', 8);
        """)
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS token_kinds (
          token_kind    CHAR(1)       PRIMARY KEY NOT NULL,
          seq     INTEGER UNIQUE
        );
        /* ERC20 */
        INSERT OR IGNORE INTO token_kinds(token_kind, seq) VALUES ('A', 1);
        /* ERC721 */
        INSERT OR IGNORE INTO token_kinds(token_kind, seq) VALUES ('B', 2);
        /* UNKNOWN */
        INSERT OR IGNORE INTO token_kinds(token_kind, seq) VALUES ('C', 3);
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            identifier TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
            name TEXT,
            type CHAR(1) NOT NULL DEFAULT('A') REFERENCES asset_types(type),
            started INTEGER,
            swapped_for TEXT,
            FOREIGN KEY(swapped_for) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE SET NULL
        );
        """)  # noqa: E501
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS common_asset_details(
            identifier TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
            symbol TEXT,
            coingecko TEXT,
            cryptocompare TEXT,
            forked TEXT,
            FOREIGN KEY(forked) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE SET NULL,
            FOREIGN KEY(identifier) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE
        );
        """)  # noqa: E501
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS evm_tokens (
            identifier TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
            token_kind CHAR(1) NOT NULL DEFAULT('A') REFERENCES token_kinds(token_kind),
            chain CHAR(1) NOT NULL DEFAULT('A') REFERENCES chain_ids(chain),
            address VARCHAR[42] NOT NULL,
            decimals INTEGER,
            protocol TEXT,
            FOREIGN KEY(identifier) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE
        );
        """)  # noqa: E501
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS multiasset_mappings(
            collection_id INTEGER NOT NULL,
            asset TEXT NOT NULL,
            FOREIGN KEY(collection_id) REFERENCES asset_collections(id) ON UPDATE CASCADE ON DELETE CASCADE,
            FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE
        );
        """)  # noqa: E501
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_owned_assets (
            asset_id VARCHAR[24] NOT NULL PRIMARY KEY,
            FOREIGN KEY(asset_id) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS underlying_tokens_list (
            identifier TEXT NOT NULL,
            weight TEXT NOT NULL,
            parent_token_entry TEXT NOT NULL,
            FOREIGN KEY(parent_token_entry) REFERENCES evm_tokens(identifier)
                ON DELETE CASCADE ON UPDATE CASCADE
            FOREIGN KEY(identifier) REFERENCES evm_tokens(identifier) ON UPDATE CASCADE ON DELETE CASCADE
            PRIMARY KEY(identifier, parent_token_entry)
        );
        """)  # noqa: E501
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
        CREATE TABLE IF NOT EXISTS asset_collections(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            symbol TEXT NOT NULL
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_assets(
            identifier TEXT NOT NULL PRIMARY KEY,
            name TEXT NOT NULL,
            notes TEXT,
            type TEXT,
            FOREIGN KEY(identifier) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE
        );
        """)  # noqa: E501
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS binance_pairs (
        pair TEXT NOT NULL,
        base_asset TEXT NOT NULL,
        quote_asset TEXT NOT NULL,
        location TEXT NOT NULL,
        FOREIGN KEY(base_asset) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
        FOREIGN KEY(quote_asset) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
        PRIMARY KEY(pair, location)
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS general_cache (
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            last_queried_ts INTEGER NOT NULL,
            PRIMARY KEY(key, value)
        );
        """)

        # And now input the modified data back to the new tables
        cursor.executescript('PRAGMA foreign_keys=off;')
        cursor.executemany(COMMON_ASSETS_INSERT, common_asset_details)
        cursor.executemany(COMMON_ASSETS_INSERT, common_asset_details_others)
        cursor.executemany(ASSETS_INSERT, assets_tuple)
        cursor.executemany(ASSETS_INSERT, assets_tuple_others)
        cursor.executemany(OWNED_ASSETS_INSERT, owned_assets)
        cursor.executemany(PRICES_INSERT, updated_prices)
        cursor.executemany(BINANCE_INSERT, updated_binance_pairs)
        cursor.executescript('PRAGMA foreign_keys=on;')
        cursor.executemany(EVM_TOKEN_INSERT, evm_tuples)
        cursor.executemany(UNDERLYING_TOKEN_INSERT, mappings)

        dir_path = Path(__file__).resolve().parent.parent.parent
        # This file contains the EVM version of the assets that are currently in the
        # database and are not EVM (matic tokens, Otimism tokens, etc) + their variants in
        # other chains. And populates them properly via sql statements
        with open(dir_path / 'data' / 'globaldb_v2_v3_assets.sql', 'r') as f:
            sql_sentences = f.read()
            cursor.executescript(sql_sentences)
        connection.commit()
