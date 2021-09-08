import logging
import sqlite3
from collections import deque
from typing import Deque, Dict, Tuple, Any, List
import random

from rotkehlchen.chain.ethereum.typing import string_to_ethereum_address
from rotkehlchen.constants.resolver import (
    ChainID,
    EvmTokenKind,
    VALID_EVM_CHAINS,
    EVM_CHAINS_TO_DATABASE,
    evm_address_to_identifier,
    translate_old_format_to_new,
)
from rotkehlchen.globaldb.schema import (
    DB_V3_CREATE_COMMON_ASSETS_DETAILS,
    DB_V3_CREATE_ASSETS,
    DB_V3_CREATE_EVM_TOKENS,
    DB_V3_CREATE_MULTIASSETS,
    DB_CREATE_EVM_TOKENS_LIST,
    DB_CREATE_USER_OWNED_ASSETS,
)
from rotkehlchen.typing import ChecksumEthAddress

log = logging.getLogger(__name__)


COMMON_ASSETS_INSERT = """INSERT OR IGNORE INTO common_asset_details(
    identifier, name, symbol, coingecko, cryptocompare, forked
    ) VALUES(?, ?, ?, ?, ?, ?)
"""
ASSETS_INSERT = """INSERT OR IGNORE INTO assets(
        identifier, type, started, swapped_for, common_details_id
    )VALUES(?, ?, ?, ?, ?);
"""
EVM_TOKEN_INSERT = """INSERT OR IGNORE INTO evm_tokens(
        identifier, token_type, chain, address, decimals, protocol
    ) VALUES(?, ?, ?, ?, ?, ?)
"""
UNDERLYING_TOKEN_INSERT = """INSERT OR IGNORE INTO
    underlying_tokens_list(identifier, weight, parent_token_entry)
    VALUES (?, ?, ?)
"""
OWNED_ASSETS_INSERT = 'INSERT OR IGNORE INTO user_owned_assets(asset_id) VALUES (?);'
MIGRATION_CACHE: Deque[Any] = deque([])

EVM_TUPLES_CREATION_TYPE = (
    Tuple[
        List[Tuple[Any, int, int, Any, Any, Any]],
        List[Tuple[Any, str, Any, str, Any]],
        List[Tuple[Any, Any, Any, Any, Any, None]],
    ]
)

ASSET_CREATION_TYPE = (
    Tuple[
        List[Tuple[Any, str, Any, str, Any]],
        List[Tuple[Any, Any, Any, Any, Any, None]],
    ]
)


def coingecko_hack() -> Dict[str, ChecksumEthAddress]:
    """Avoid querying coingecko for now"""
    # TODO assets: This is a hack just for having a fist implementation
    addr = string_to_ethereum_address(
        '0x' + "".join(random.choices('0123456789ABCDEFabcdef', k=40)),
    )
    return {str(k): addr for k in ChainID}


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
            entry[0],  # identifier
            EvmTokenKind.ERC20.value,  # token type
            ChainID.ETHEREUM.value,  # chain
            entry[1],  # address
            entry[2],  # decimals
            entry[3],  # protocol
        ))
        new_swapped_for = old_ethereum_id_to_new.get(entry[8], entry[8])
        assets_tuple.append((
            entry[0],  # identifier
            'C',  # type
            entry[7],  # started
            new_swapped_for,  # swapped for
            entry[0],  # common_details_id
        ))
        common_asset_details.append((
            entry[0],  # identifier
            entry[5],  # name
            entry[6],  # symbol
            entry[9],  # coingecko
            entry[10],  # cryptocompare
            None,  # forked
        ))

    return (
        evm_tuples,
        assets_tuple,
        common_asset_details,
    )


def evm_compatible_assets_create_tuples(
    query: List[Any],
) -> EVM_TUPLES_CREATION_TYPE:
    """Get information from globaldb and transform it to evm compatible structure"""
    old_id_to_new = {}
    evm_tuples = []
    assets_tuple = []
    common_asset_details = []

    for entry in query:
        try:
            ids = coingecko_hack()
            asset_chain = VALID_EVM_CHAINS[entry[1]]
        except KeyError as e:
            msg = str(e)
            log.error(f'Failed to fetch coingecko information for EVM asset {entry[0]}. {msg}')

        # Continue with the migration
        address = ids[str(asset_chain)]
        new_id = evm_address_to_identifier(
            address=address,  # We have to query for this
            chain=asset_chain,
            token_type=EvmTokenKind.ERC20,
            collectible_id=None,
        )

        old_id_to_new[entry[0]] = new_id
        new_swapped_for = old_id_to_new.get(entry[8], entry[8])
        evm_tuples.append((
            new_id,  # identifier
            EvmTokenKind.ERC20.value,  # token type
            asset_chain.value,  # chain
            address,  # address
            None,  # decimals TODO: We have to query this information
            None,  # protocol
        ))
        assets_tuple.append((
            new_id,  # identifier
            EVM_CHAINS_TO_DATABASE[asset_chain],  # type
            entry[4],  # started
            new_swapped_for,  # swapped for
            new_id,  # common_details_id
        ))
        common_asset_details.append((
            new_id,  # identifier
            entry[2],  # name
            entry[3],  # symbol
            entry[5],  # coingecko
            entry[6],  # cryptocompare
            None,  # forked TODO: Add the forked field
        ))

    return (
        evm_tuples,
        assets_tuple,
        common_asset_details,
    )


def upgrade_evm_compatible_assets(connection: sqlite3.Connection) -> EVM_TUPLES_CREATION_TYPE:
    cursor = connection.cursor()
    chains = ",".join([f'"{x}"' for x in VALID_EVM_CHAINS])
    result = cursor.execute(f'SELECT * FROM assets WHERE type IN ({chains})')
    return evm_compatible_assets_create_tuples(result.fetchall())


def upgrade_other_assets(connection: sqlite3.Connection) -> ASSET_CREATION_TYPE:
    cursor = connection.cursor()
    chains = ",".join([f'"{x}"' for x in (*VALID_EVM_CHAINS.keys(), 'C')])
    result = cursor.execute(f'SELECT * FROM assets WHERE type NOT IN ({chains})')

    assets_tuple = []
    common_asset_details = []

    for entry in result:
        assets_tuple.append((
            entry[0],  # identifier
            entry[1],  # type
            entry[4],  # started
            entry[5],  # swapped for
            entry[0],  # common_details_id
        ))
        common_asset_details.append((
            entry[0],  # identifier
            entry[2],  # name
            entry[3],  # symbol
            entry[5],  # coingecko
            entry[6],  # cryptocompare
            None,  # forked TODO: Add the forked field
        ))

    return (
        assets_tuple,
        common_asset_details,
    )


def upgrade_ethereum_asset_ids_v3(connection: sqlite3.Connection) -> EVM_TUPLES_CREATION_TYPE:
    # Get all ethereum ids
    cursor = connection.cursor()
    result = cursor.execute(
        'SELECT A.address, A.decimals, A.protocol, B.identifier, B.name, B.symbol, B.started, '
        'B.swapped_for, B.coingecko, B.cryptocompare FROM assets '
        'AS B JOIN ethereum_tokens '
        'AS A ON A.address = B.details_reference WHERE B.type="C";',
    )

    return upgrade_ethereum_assets(result.fetchall())


def translate_underlying_table(connection: sqlite3.Connection) -> List[Tuple[str, str, str]]:
    """For this traslation we know that we only stored ethereum tokens"""
    cursor = connection.cursor()
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


def translate_user_owned_assets(connection: sqlite3.Connection) -> List[Tuple[str]]:
    cursor = connection.cursor()
    query = cursor.execute(
        'SELECT A.identifier, A.type from assets AS A JOIN user_owned_assets '
        'AS B on A.identifier=B.asset_id;',
    )
    owned_assets = []
    for entry in query:
        if VALID_EVM_CHAINS.get(entry[1]) is not None:
            ids = coingecko_hack()
            asset_chain = VALID_EVM_CHAINS[entry[1]]
            # TODO assets: This can be broken now for EVM assets since we use random generated
            # addresses. After a proper implementation should work always
            address = ids[str(asset_chain)]
            idenfifier = evm_address_to_identifier(
                address=address,  # We have to query for this
                chain=asset_chain,
                token_type=EvmTokenKind.ERC20,
                collectible_id=None,
            )
            owned_assets.append((idenfifier,))
        else:
            owned_assets.append((translate_old_format_to_new(entry[0]),))

    return owned_assets


def migrate_to_v3(connection: sqlite3.Connection) -> None:
    """Upgrade assets information and migrate globaldb to version 3"""

    cursor = connection.cursor()
    # Obtain information for ethereum assets
    evm_tuples, assets_tuple, common_asset_details = upgrade_ethereum_asset_ids_v3(connection)
    # Obtain information for chains that are evm compatible already in the database
    output = upgrade_evm_compatible_assets(connection)
    evm_tuples_other, assets_tuple_other, common_asset_details_other = output
    # Obtain information for other assets
    assets_non_evm, common_assets_non_evm = upgrade_other_assets(connection)
    # Underlying tokens mappings
    mappings = translate_underlying_table(connection)
    # Owned assets with updated ids
    owned_assets = translate_user_owned_assets(connection)

    evm_tuples += evm_tuples_other
    assets_tuple += assets_tuple_other
    common_asset_details += common_asset_details_other
    assets_tuple += assets_non_evm
    common_asset_details += common_assets_non_evm

    # Purge or delete tables with outdated information
    cursor.executescript("""
    PRAGMA foreign_keys=off;
    DROP TABLE IF EXISTS user_owned_assets;
    DROP TABLE IF EXISTS assets;
    DROP TABLE IF EXISTS ethereum_tokens;
    DROP TABLE IF EXISTS common_asset_details;
    DROP TABLE IF EXISTS underlying_tokens_list;
    PRAGMA foreign_keys=on;
    """)

    # Create new tables
    cursor.execute(DB_V3_CREATE_COMMON_ASSETS_DETAILS)
    cursor.execute(DB_V3_CREATE_ASSETS)
    cursor.execute(DB_V3_CREATE_EVM_TOKENS)
    cursor.execute(DB_V3_CREATE_MULTIASSETS)
    cursor.execute(DB_CREATE_EVM_TOKENS_LIST)
    cursor.execute(DB_CREATE_USER_OWNED_ASSETS)

    cursor.executemany(COMMON_ASSETS_INSERT, common_asset_details)
    cursor.executemany(ASSETS_INSERT, assets_tuple)
    cursor.executemany(EVM_TOKEN_INSERT, evm_tuples)
    cursor.executemany(UNDERLYING_TOKEN_INSERT, mappings)
    cursor.executemany(OWNED_ASSETS_INSERT, owned_assets)

    connection.commit()
