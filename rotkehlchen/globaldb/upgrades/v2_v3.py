import logging
import sqlite3
from collections import defaultdict, deque
from typing import Dict, Tuple, Any, List
import random

from eth_utils import to_checksum_address
import requests

from rotkehlchen.constants.resolver import (
    CHAINID,
    EvmTokenKind,
    VALID_EVM_CHAINS,
    EVM_CHAINS_TO_DATABASE,
    evm_address_to_identifier,
)
from rotkehlchen.globaldb.schema import (
    DB_V3_CREATE_COMMON_ASSETS_DETAILS,
    DB_V3_CREATE_ASSETS,
    DB_V3_CREATE_EVM_TOKENS,
    DB_V3_CREATE_ASSETS_EVM_TOKENS,
    DB_V3_CREATE_MULTIASSETS,
    DB_CREATE_ETHEREUM_TOKENS_LIST,
)

log = logging.getLogger(__name__)


COMMON_ASSETS_INSERT = (
    """INSERT OR IGNORE INTO common_asset_details(
        identifier, name, symbol, coingecko, cryptocompare, forked
        ) VALUES(?, ?, ?, ?, ?, ?)"""
)
ASSETS_INSERT = (
    """INSERT OR IGNORE INTO assets(
            identifier, type, started, swapped_for, common_details_id
        )VALUES(?, ?, ?, ?, ?);"""
)
EVM_TOKEN_INSERT = (
    """INSERT OR IGNORE INTO evm_tokens(
            identifier, token_type, chain, address, decimals, protocol
        ) VALUES(?, ?, ?, ?, ?, ?)"""
)
UNDERLYING_TOKEN_INSERT(
    """INSERT OR IGNORE INTO underlying_tokens_list(identifier, weight, parent_token_entry)
        VALUES (?, ?, ?)"""
)
OWNED_ASSETS_INSERT = 'INSERT OR IGNORE INTO user_owned_assets(asset_id) VALUES (?);'
MIGRATION_CACHE = deque([])


def coingecko_hack() -> Dict[CHAINID, str]:
    """Avoid querying coingecko for now"""
    # TODO ASSETS: Remove this hack
    addr = '0x' + "".join(random.choices('0123456789ABCDEFabcdef', k=40))
    return {k.value: addr for k in CHAINID}


def query_coingecko_for_addresses(id: str) -> Dict[CHAINID, str]:
    """
    Call coingecko API to obtain asset addresses in other chains.
    Can raise:
    - RemoteError
    - KeyError
    """
    # Hack this function for now since we need this mapping for the migration
    return coingecko_hack()

    url = 'https://api.coingecko.com/api/v3/coins/{coin_id}?tickers=false&market_data=false&developer_data=true&sparkline=false'  # noqa: E501
    req = requests.get(url.format(coin_id=id))
    data = req.json()
    output = {}
    for platform, addr in data['platforms'].items():
        if len(addr):
            output[CHAINID.deserialize_from_coingecko(platform).value] = to_checksum_address(addr)
    return output


def upgrade_ethereum_assets(query: List[Any]) -> Tuple[Any]:
    old_ethereum_data = []
    old_ethereum_id_to_new = {}
    evm_tuples = []
    assets_tuple = []
    common_asset_details = []

    for entry in query:
        new_id = evm_address_to_identifier(
            address=entry[0],
            chain=CHAINID.ETHEREUM_CHAIN_IDENTIFIER,
            token_type=EvmTokenKind.ERC20,
            collectible_id=None,
        )
        old_ethereum_id_to_new[entry[3]] = new_id
        old_ethereum_data.append((new_id, *entry))

    for entry in old_ethereum_data:
        evm_tuples.append((
            entry[0],  # identifier
            EvmTokenKind.ERC20.value,  # token type
            CHAINID.ETHEREUM_CHAIN_IDENTIFIER.value,  # chain
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
) -> Tuple[Any]:
    """Get information from globaldb and transform it to evm compatible structure"""
    old_asset_data = []
    old_id_to_new = {}
    evm_tuples = []
    assets_tuple = []
    common_asset_details = []

    for entry in query:
        try:
            ids = query_coingecko_for_addresses(entry[6])
            asset_chain = VALID_EVM_CHAINS[entry[1]]
        except KeyError as e:
            msg = str(e)
            log.error(f'Failed to fetch coingecko information for EVM asset {entry[0]}. {msg}')
        # For the new addresses we got we have to add them later
        for pair in ids.items():
            # TODO assets: This logic has to be implemented but maybe outside this cycle
            # of events.
            MIGRATION_CACHE.append((*pair, *entry))

        # Continue with the migration
        address = ids[asset_chain.value]
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


def upgrade_evm_compatible_assets(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    chains = ",".join([f'"{x}"' for x in VALID_EVM_CHAINS.keys()])
    result = cursor.execute(f'SELECT * FROM assets WHERE type IN ({chains})')

    evm_tuples, assets_tuple, common_asset_details = evm_compatible_assets_create_tuples(result)

    return (
        evm_tuples,
        assets_tuple,
        common_asset_details
    )


def upgrade_other_assets(connection: sqlite3.Connection) -> Tuple[Any]:
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


def upgrade_ethereum_asset_ids_v3(connection: sqlite3.Connection) -> Tuple[Any]:
    # Get all ethereum ids
    cursor = connection.cursor()
    result = cursor.execute('SELECT * from underlying_tokens_list;')
    underlying_tokens_list_tuples = result.fetchall()
    result = cursor.execute(
        'SELECT A.address, A.decimals, A.protocol, B.identifier, B.name, B.symbol, B.started, '
        'B.swapped_for, B.coingecko, B.cryptocompare FROM assets '
        'AS B JOIN ethereum_tokens '
        'AS A ON A.address = B.details_reference WHERE B.type="C";',
    )

    return upgrade_ethereum_assets(result)


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
            chain=CHAINID.ETHEREUM_CHAIN_IDENTIFIER,
            token_type=EvmTokenKind.ERC20,
            collectible_id=None,
        )
        new_parent = evm_address_to_identifier(
            address=row[2],
            chain=CHAINID.ETHEREUM_CHAIN_IDENTIFIER,
            token_type=EvmTokenKind.ERC20,
            collectible_id=None,
        )
        mappings.append((new_address, row[1], new_parent))
    return mappings


def translate_user_owned_assets(connection: sqlite3.Connection) -> List[Tuple[str, str, str]]:
    cursor = connection.cursor()
    query = cursor.execute(
        'SELECT A.identifier, A.type from assets AS A JOIN user_owned_assets '
        'AS B on A.identifier=B.asset_id;',
    )
    owned_assets = []
    for asset in query:
        if VALID_EVM_CHAINS.get(entry[1]) is not None:
            ids = query_coingecko_for_addresses(entry[0])
            asset_chain = VALID_EVM_CHAINS[entry[1]]
            # TODO assets: This can be broken now for EVM assets since we use random generated
            # addresses. After a proper implementation should work always
            address = ids[asset_chain.value]
            idenfifier = evm_address_to_identifier(
                address=address,  # We have to query for this
                chain=asset_chain,
                token_type=EvmTokenKind.ERC20,
                collectible_id=None,
            )
            owned_assets.append((dentifier,))
    return owned_assets


def migrate_to_v3(connection: sqlite3.Connection) -> None:
    """Upgrade assets information and migrate globaldb to version 3"""

    cursor = connection.cursor()
    # Obtain information for ethereum assets
    evm_tuples, assets_tuple, common_asset_details = upgrade_ethereum_asset_ids_v3(connection)
    # Obtain information for chains that are evm compatibles already in the database
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
    cursor.execute(DB_V3_CREATE_ASSETS_EVM_TOKENS)
    cursor.execute(DB_V3_CREATE_MULTIASSETS)
    cursor.execute(DB_CREATE_ETHEREUM_TOKENS_LIST)
    cursor.execute(DB_CREATE_USER_OWNED_ASSETS)

    cursor.executemany(COMMON_ASSETS_INSERT, common_asset_details)
    cursor.executemany(ASSETS_INSERT, assets_tuple)
    cursor.executemany(EVM_TOKEN_INSERT, evm_tuples)
    cursor.executemany(UNDERLYING_TOKEN_INSERT, mappings)
    cursor.executemany(OWNED_ASSETS_INSERT, owned_assets)

    connection.commit()
