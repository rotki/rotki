import json
import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING

from eth_utils.address import to_checksum_address

from rotkehlchen.assets.asset import Asset, CryptoAsset
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_WETH
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    CacheType,
    ChainID,
    ChecksumEvmAddress,
    EvmTokenKind,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.drivers.sqlite import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# a bit hacky but ETH-A ilk is our general update ilk cache timestamp reminder
GENERAL_ILK_CACHE_KEY = f'{CacheType.MAKERDAO_VAULT_ILK.serialize()}ETH-A'


def _collateral_type_to_info(
        cursor: 'DBCursor',
        collateral_type: str,
) -> tuple[int, ChecksumEvmAddress, ChecksumEvmAddress] | None:
    cursor.execute(
        'SELECT value from unique_cache WHERE key=?',
        (f'{CacheType.MAKERDAO_VAULT_ILK.serialize()}{collateral_type}',),
    )
    result = cursor.fetchone()
    if result is None:
        return None

    try:
        info = json.loads(result[0])
    except json.JSONDecodeError:
        log.error(f'Ilk {collateral_type} cache value {result[0]} could not be deserialized as json')  # noqa: E501
        return None

    return int(info[0]), info[1], info[2]


def collateral_type_to_underlying_asset(collateral_type: str) -> CryptoAsset | None:
    """Get the underlying asset for a collateral type by asking the global DB cache"""
    with GlobalDBHandler().conn.read_ctx() as cursor:
        info = _collateral_type_to_info(cursor, collateral_type)

    if info is None:
        return None

    try:
        underlying_asset = Asset(info[1]).resolve_to_crypto_asset()
    except (WrongAssetType, UnknownAsset) as e:
        log.error(f'Ilk {collateral_type} asset {info[0]} could not be initialized due to {e!s}.')
        return None

    # note sure if special case needed but this makes it equivalent with how code was with mappings
    return A_ETH if underlying_asset == A_WETH else underlying_asset  # type: ignore


def ilk_cache_foreach(
        cursor: 'DBCursor',
) -> Iterator[tuple[str, int, CryptoAsset, ChecksumEvmAddress]]:
    """Reads the ilk cache from the globalDB and yields at each iteration of the cursor"""
    cache_prefix = CacheType.MAKERDAO_VAULT_ILK.serialize()
    len_prefix = len(cache_prefix)
    cursor.execute(
        'SELECT key, value from unique_cache WHERE key LIKE ?',
        (f'{cache_prefix}%',),
    )
    for cache_key, entry in cursor:
        ilk = cache_key[len_prefix:]
        try:
            info = json.loads(entry)
        except json.JSONDecodeError:
            log.error(f'Ilk {ilk} cache value {entry} could not be deserialized as json. Skipping')
            continue

        try:
            underlying_asset = Asset(info[1]).resolve_to_crypto_asset()
        except (WrongAssetType, UnknownAsset) as e:
            log.error(f'Ilk {ilk} asset {info[1]} could not be initialized due to {e!s}. Skipping')
            continue

        yield ilk, int(info[0]), underlying_asset, info[2]


def query_ilk_registry(
        ethereum: 'EthereumInquirer',
) -> dict[str, tuple[int, ChecksumEvmAddress, ChecksumEvmAddress]]:
    """Queries ilk registry for some info
    https://github.com/makerdao/ilk-registry

    Returns (ilk_class, gem_address, join_adapter_address)

    gem_address is the token_address
    For different ilk classes value check here:
    https://etherscan.io/address/0x5a464C28D19848f44199D003BeF5ecc87d090F87#code

    At the moment of writing it's:
    //  1   - Flipper
    //  2   - Clipper
    //  3-4 - RWA or custom adapter

    And there is no (2) in the registry.

    May raise:
    - RemoteError if any of the remote queries fail
    """
    ilks_mapping = {}
    ilk_registry = ethereum.contracts.contract(string_to_evm_address('0x5a464C28D19848f44199D003BeF5ecc87d090F87'))  # noqa: E501
    ilks_num = ilk_registry.call(ethereum, method_name='count')
    step = 20  # split into multiple multi-calls to not hit etherscan or gas limits
    for idx in range(0, ilks_num, step):
        ilks = ilk_registry.call(
            ethereum,
            method_name='list',
            arguments=[idx, min(idx + step - 1, ilks_num - 1)],
        )
        info_calls = [
            (ilk_registry.address, ilk_registry.encode(method_name='info', arguments=[x]))
            for x in ilks
        ]
        outputs = ethereum.multicall_2(
            require_success=False,
            calls=info_calls,
        )
        for output_idx, output in enumerate(outputs):
            status, result = output
            if status is False:
                log.error(f'Part of a multicall to ilk registry failed: {info_calls[output_idx]}')
                continue
            ilk = ilks[output_idx]
            collateral_type = ilk.split(b'\0', 1)[0].decode()
            info = ilk_registry.decode(result, 'info', arguments=[ilk])
            gem_address = to_checksum_address(info[4])
            join_address = to_checksum_address(info[6])
            ilks_mapping[collateral_type] = (info[2], gem_address, join_address)

    return ilks_mapping


def update_ilk_registry(
        ethereum: 'EthereumInquirer',
        ilk_mappings: dict[str, tuple[int, ChecksumEvmAddress, ChecksumEvmAddress]],
) -> None:
    """Uses the queried ilk registry data and updates the global DB ilk cache by
    doing the following for each ilk:

    - If the ilk is in the global DB do nothing
    - If it's not then query join address deployed block and abi
    - Add them to the global DB
    - Queue the ilk for writing to the cache
    - Write all queued data to the cache
    """
    now = ts_now()
    with GlobalDBHandler().conn.read_ctx() as cursor:
        write_tuples = []
        for ilk, (ilk_class, token_address, join_address) in ilk_mappings.items():

            if ZERO_ADDRESS in (
                token_address,  # happens for at least TELEPORT-FW-A
                join_address,  # happens for at least LITE-PSM-USDC-A
            ):
                continue  # ignore those cases

            cursor.execute(
                'SELECT COUNT(*) from unique_cache WHERE key=?',
                (f'{CacheType.MAKERDAO_VAULT_ILK.serialize()}{ilk}',),
            )
            if cursor.fetchone()[0] != 0:
                continue  # already exists

            try:
                deployed_block = ethereum.get_contract_deployed_block(join_address)
                abi = ethereum.etherscan.get_contract_abi(
                    chain_id=ChainID.ETHEREUM,
                    address=join_address,
                )
            except RemoteError as e:
                log.error(f'Did not add ilk {ilk} due to inability to query contract {join_address} metadata: {e!s}')  # noqa: E501
                continue

            if None in (deployed_block, abi):
                log.error(f'Did not add ilk {ilk} due to no response for {join_address} metadata')
                continue

            abi_name = f'MAKERDAO_{ilk}_JOIN'
            abi_id = GlobalDBHandler.get_or_write_abi(
                serialized_abi=json.dumps(abi, separators=(',', ':')),
                abi_name=abi_name,
            )
            cursor.execute(
                'SELECT COUNT(*) FROM contract_data WHERE address=? and chain_id=?',
                (join_address, 1),
            )
            if cursor.fetchone()[0] != 0:
                continue  # already exists

            with GlobalDBHandler().conn.write_ctx() as write_cursor:
                write_cursor.execute(
                    'INSERT INTO contract_data(address, chain_id, abi, deployed_block)'
                    ' VALUES(? ,?, ?, ?)',
                    (join_address, 1, abi_id, deployed_block),
                )

            # if the underlying token does not exist, add it
            underlying_token = get_or_create_evm_token(
                userdb=ethereum.database,
                chain_id=ChainID.ETHEREUM,
                evm_address=token_address,
                token_kind=EvmTokenKind.ERC20,
                evm_inquirer=ethereum,
                encounter=TokenEncounterInfo(description='Querying makerdao collaterals registry'),
            )

            # also add to tuples to write to cache
            write_tuples.append((
                f'{CacheType.MAKERDAO_VAULT_ILK.serialize()}{ilk}',
                json.dumps((ilk_class, underlying_token.identifier, join_address), separators=(',', ':')),  # noqa: E501
                now,
            ))

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        # since the unique cache is unique for every key, the value will be overwritten.
        if len(write_tuples) != 0:
            write_cursor.executemany(
                'INSERT OR REPLACE INTO unique_cache(key, value, last_queried_ts) VALUES(?, ?, ?)',
                write_tuples,
            )

        write_cursor.execute(
            'UPDATE unique_cache SET last_queried_ts=? WHERE key=?',
            (now, GENERAL_ILK_CACHE_KEY),
        )


def query_ilk_registry_and_maybe_update_cache(ethereum: 'EthereumInquirer') -> None:
    """
    Query the on-chain ilk registry, and for any collateral type that is not yet known,
    pull it's contract data, put it in the DB and then add it in the cache.

    May raise:
    - RemoteError if any of the remote queries fail
    """
    ilk_mappings = query_ilk_registry(ethereum)
    update_ilk_registry(ethereum, ilk_mappings)
