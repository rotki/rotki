import logging
from typing import TYPE_CHECKING, Optional

from eth_utils import to_checksum_address

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import TokenSeenAt, get_or_create_evm_token
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS, ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.misc import NotERC20Conformant
from rotkehlchen.globaldb.cache import (
    compute_cache_key,
    globaldb_delete_general_cache,
    globaldb_delete_general_cache_like,
    globaldb_get_general_cache_keys_and_values_like,
    globaldb_get_general_cache_values,
    globaldb_set_general_cache_values,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    CURVE_POOL_PROTOCOL,
    ChainID,
    ChecksumEvmAddress,
    EvmTokenKind,
    GeneralCacheType,
)
from rotkehlchen.utils.misc import hex_or_bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

CURVE_POOLS_MAPPING_TYPE = dict[
    ChecksumEvmAddress,  # lp token address
    tuple[
        ChecksumEvmAddress,  # pool address
        list[ChecksumEvmAddress],  # list of coins addresses
        Optional[list[ChecksumEvmAddress]],  # optional list of underlying coins addresses
    ],
]

READ_CURVE_DATA_TYPE = tuple[
    dict[ChecksumEvmAddress, list[ChecksumEvmAddress]],
    set[ChecksumEvmAddress],

]
# list of pools that we know contain bad tokens
IGNORED_CURVE_POOLS = {'0x066B6e1E93FA7dcd3F0Eb7f8baC7D5A747CE0BF9'}

# Using any random address here, since length of all addresses is the same
BASE_POOL_TOKENS_KEY_LENGTH = len(compute_cache_key([GeneralCacheType.CURVE_POOL_TOKENS, ZERO_ADDRESS]))  # noqa: E501


def read_curve_data(
        cursor: 'DBCursor',
        pool_address: ChecksumEvmAddress,
) -> list[ChecksumEvmAddress]:
    """
    Reads tokens for a particular curve pool. Tokens are stored with their indices to make sure
    that the order of coins in pool contract and in our cache is the same. This functions reads
    and returns tokens in sorted order.
    """
    tokens_data = globaldb_get_general_cache_keys_and_values_like(
        cursor=cursor,
        key_parts=[GeneralCacheType.CURVE_POOL_TOKENS, pool_address],
    )
    found_tokens: list[tuple[int, ChecksumEvmAddress]] = []
    for key, address in tokens_data:
        index = int(key[BASE_POOL_TOKENS_KEY_LENGTH:])  # len(key) > BASE_POOL_TOKENS_KEY_LENGTH
        found_tokens.append((index, string_to_evm_address(address)))

    found_tokens.sort(key=lambda x: x[0])
    return [address for _, address in found_tokens]


def read_curve_pools_and_gauges() -> READ_CURVE_DATA_TYPE:
    """Reads globaldb cache and returns:
    - A set of all known curve pools addresses.
    - A set of all known curve gauges addresses.

    Doesn't raise anything unless cache entries were inserted incorrectly.
    """
    with GlobalDBHandler().conn.read_ctx() as cursor:
        curve_pools_lp_tokens = globaldb_get_general_cache_values(
            cursor=cursor,
            key_parts=[GeneralCacheType.CURVE_LP_TOKENS],
        )
        curve_pools = {}
        curve_gauges = set()
        for lp_token_addr in curve_pools_lp_tokens:
            pool_address = globaldb_get_general_cache_values(
                cursor=cursor,
                key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, lp_token_addr],
            )[0]
            gauge_address_data = globaldb_get_general_cache_values(
                cursor=cursor,
                key_parts=[GeneralCacheType.CURVE_GAUGE_ADDRESS, pool_address],
            )
            if len(gauge_address_data) > 0:
                curve_gauges.add(string_to_evm_address(gauge_address_data[0]))
            pool_address = string_to_evm_address(pool_address)
            curve_pools[pool_address] = read_curve_data(cursor=cursor, pool_address=pool_address)  # noqa: E501

    return curve_pools, curve_gauges


def ensure_curve_tokens_existence(
        ethereum_inquirer: 'EthereumInquirer',
        pools_mapping: CURVE_POOLS_MAPPING_TYPE,
) -> CURVE_POOLS_MAPPING_TYPE:
    """This function receives data about curve pools and ensures that lp tokens and pool coins
    exist in rotki's database.

    Since is possible that a pool has an invalid token we keep a mapping of the valid ones
    and return it.

    May raise:
    - NotERC20Conformant if failed to query info while calling get_or_create_evm_token

    """
    updated_pools_mapping = {}
    for lp_token_address, pool_info in pools_mapping.items():
        _, coins, underlying_coins = pool_info
        # Ensure pool coins exist in the globaldb.
        # We have to create underlying tokens only if pool utilizes them.
        if underlying_coins is None or underlying_coins == coins:
            # If underlying coins is None, it means that pool doesn't utilize them.
            # If underlying coins list is equal to coins then there are no underlying coins as well.  # noqa: E501
            for token_address in coins:
                if token_address == ETH_SPECIAL_ADDRESS:
                    continue
                # ensure token exists
                try:
                    get_or_create_evm_token(
                        userdb=ethereum_inquirer.database,
                        evm_address=token_address,
                        chain_id=ChainID.ETHEREUM,
                        evm_inquirer=ethereum_inquirer,
                        seen=TokenSeenAt(description='Querying curve pools'),
                    )
                except NotERC20Conformant as e:
                    log.info(
                        f'Skipping pool {pool_info} because {token_address} is not a '
                        f'valid ERC20 token. {str(e)}',
                    )
                    continue
        else:
            # Otherwise, coins and underlying coins lists represent a
            # mapping of coin -> underlying coin (each coin always has one underlying coin).
            for token_address, underlying_token_address in zip(coins, underlying_coins):
                if token_address == ETH_SPECIAL_ADDRESS:
                    continue
                # ensure underlying token exists
                try:
                    get_or_create_evm_token(
                        userdb=ethereum_inquirer.database,
                        evm_address=underlying_token_address,
                        chain_id=ChainID.ETHEREUM,
                        evm_inquirer=ethereum_inquirer,
                        seen=TokenSeenAt(description='Querying curve pools'),
                    )
                except NotERC20Conformant as e:
                    log.info(
                        f'Skipping pool {pool_info} because {underlying_token_address} is not a '
                        f'valid ERC20 token. {str(e)}',
                    )
                    continue

                try:
                    # and ensure token exists
                    get_or_create_evm_token(
                        userdb=ethereum_inquirer.database,
                        evm_address=token_address,
                        chain_id=ChainID.ETHEREUM,
                        evm_inquirer=ethereum_inquirer,
                        underlying_tokens=[UnderlyingToken(
                            address=underlying_token_address,
                            token_kind=EvmTokenKind.ERC20,
                            weight=ONE,
                        )],
                        seen=TokenSeenAt(description='Querying curve pools'),
                    )
                except NotERC20Conformant as e:
                    log.info(
                        f'Skipping pool {pool_info} because {token_address} is not a '
                        f'valid ERC20 token. {str(e)}',
                    )
                    continue

        # finally ensure lp token exists in the globaldb. Since is a token created by curve
        # it should always be an ERC20
        get_or_create_evm_token(
            userdb=ethereum_inquirer.database,
            evm_address=lp_token_address,
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=ethereum_inquirer,
            protocol=CURVE_POOL_PROTOCOL,
            seen=TokenSeenAt(description='Querying curve pools'),
        )
        updated_pools_mapping[lp_token_address] = pool_info

    return updated_pools_mapping


def save_curve_data_to_cache(
        write_cursor: DBCursor,
        pools_mapping: CURVE_POOLS_MAPPING_TYPE,
        gauges: dict[ChecksumEvmAddress, ChecksumEvmAddress],
) -> None:
    """Stores data received about curve pools and gauges in the cache"""
    # First, clear all curve pools related cache entries in the global DB
    curve_lp_tokens = globaldb_get_general_cache_values(
        cursor=write_cursor,
        key_parts=[GeneralCacheType.CURVE_LP_TOKENS],
    )
    for lp_token in curve_lp_tokens:
        pool_addr = globaldb_get_general_cache_values(
            cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, lp_token],
        )[0]
        globaldb_delete_general_cache_like(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_TOKENS, pool_addr],
        )
        globaldb_delete_general_cache(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, lp_token],
        )
        globaldb_delete_general_cache(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_GAUGE_ADDRESS, pool_addr],
        )
    globaldb_delete_general_cache(
        write_cursor=write_cursor,
        key_parts=[GeneralCacheType.CURVE_LP_TOKENS],
    )
    # Then, read the new pool mappings and save them in the global DB cache
    globaldb_set_general_cache_values(
        write_cursor=write_cursor,
        key_parts=[GeneralCacheType.CURVE_LP_TOKENS],
        values=pools_mapping.keys(),  # keys of pools_mapping are lp tokens
    )
    for lp_token_address, pool_info in pools_mapping.items():
        pool_address, coins, _underlying_coins = pool_info
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, lp_token_address],
            values=[pool_address],
        )
        if pool_address in gauges:
            globaldb_set_general_cache_values(
                write_cursor=write_cursor,
                key_parts=[GeneralCacheType.CURVE_GAUGE_ADDRESS, pool_address],
                values=[gauges[pool_address]],
            )
        for index, coin in enumerate(coins):
            globaldb_set_general_cache_values(
                write_cursor=write_cursor,
                key_parts=[GeneralCacheType.CURVE_POOL_TOKENS, pool_address, str(index)],
                values=[coin],
            )


def query_curve_registry_pools(
        ethereum: 'EthereumInquirer',
        registry_contract: EvmContract,
) -> CURVE_POOLS_MAPPING_TYPE:
    """Query pools from curve registry and return their mappings
    May raise:
    - RemoteError if failed to query etherscan or node
    """
    registry_pool_count = registry_contract.call(
        node_inquirer=ethereum,
        method_name='pool_count',
    )
    registry_pools_result = ethereum.multicall_specific(
        contract=registry_contract,
        method_name='pool_list',
        arguments=[(x,) for x in range(registry_pool_count)],
        decode_result=False,  # don't decode since decoding unchecksums address
    )
    pool_addresses = []
    for pool_addr_encoded in registry_pools_result:
        decoded_pool_addr = hex_or_bytes_to_address(pool_addr_encoded)  # already checksumed
        pool_addresses.append(decoded_pool_addr)

    registry_lp_tokens_result = ethereum.multicall_specific(
        contract=registry_contract,
        method_name='get_lp_token',
        arguments=[(x,) for x in pool_addresses],
        decode_result=False,  # don't decode since decoding unchecksums address
    )
    registry_coins_result = ethereum.multicall_specific(
        contract=registry_contract,
        method_name='get_coins',
        arguments=[(x,) for x in pool_addresses],
    )
    registry_underlying_coins_result = ethereum.multicall_specific(
        contract=registry_contract,
        method_name='get_underlying_coins',
        arguments=[(x,) for x in pool_addresses],
    )
    pools_mapping: CURVE_POOLS_MAPPING_TYPE = {}
    results_zip = zip(pool_addresses, registry_lp_tokens_result, registry_coins_result, registry_underlying_coins_result)  # noqa: E501
    for pool_addr, lp_token_encoded, (decoded_pool_coins,), (decoded_pool_underlying_coins,) in results_zip:  # noqa: E501
        decoded_lp_token = hex_or_bytes_to_address(lp_token_encoded)
        pool_coins = []
        pool_underlying_coins = []
        for pool_coin in decoded_pool_coins:
            checksumed_coin_addr = to_checksum_address(pool_coin)
            if checksumed_coin_addr == ZERO_ADDRESS:
                # curve returns array of fixed length. So if current pool utilizes fewer
                # coins than the array's length, first values in the result are the real
                # coins and all addresses after are just 0x00..00
                break
            pool_coins.append(checksumed_coin_addr)

        for pool_underlying_coin in decoded_pool_underlying_coins:
            checksumed_underlying_coin_addr = to_checksum_address(pool_underlying_coin)
            if checksumed_underlying_coin_addr == ZERO_ADDRESS:
                break
            pool_underlying_coins.append(checksumed_underlying_coin_addr)

        pools_mapping[decoded_lp_token] = (pool_addr, pool_coins, pool_underlying_coins)

    return pools_mapping


def query_curve_meta_pools(
        ethereum: 'EthereumInquirer',
        curve_address_provider: EvmContract,
) -> CURVE_POOLS_MAPPING_TYPE:
    """Query pools from curve metapool factory and return their mapping
    May raise:
    - RemoteError if failed to query etherscan or node
    - NotERC20Conformant if failed to query info while calling get_or_create_evm_token
    """
    factory_address_result = curve_address_provider.call(
        node_inquirer=ethereum,
        method_name='get_address',
        arguments=[3],  # 3 is metapool factory id
    )
    factory_address = to_checksum_address(factory_address_result)
    factory_contract = EvmContract(
        address=factory_address,
        abi=ethereum.contracts.abi('CURVE_METAPOOL_FACTORY'),
        deployed_block=0,  # deployment_block is not used and the contract is dynamic
    )
    pool_count = factory_contract.call(
        node_inquirer=ethereum,
        method_name='pool_count',
    )
    pool_addrs_result = ethereum.multicall_specific(
        contract=factory_contract,
        method_name='pool_list',
        arguments=[(x,) for x in range(pool_count)],
        decode_result=False,  # don't decode since decoding unchecksums address
    )
    pool_addresses = []
    for encoded_pool_addr in pool_addrs_result:
        pool_addresses.append(hex_or_bytes_to_address(encoded_pool_addr))

    # either a pool of stablecoins or a pair `stablecoin - other curve pool token`
    # so no need to query underlying tokens
    pool_coins_result = ethereum.multicall_specific(
        contract=factory_contract,
        method_name='get_coins',
        arguments=[(x,) for x in pool_addresses],
    )
    pools_mapping: CURVE_POOLS_MAPPING_TYPE = {}
    for pool_addr, (decoded_coins_result,) in zip(pool_addresses, pool_coins_result):
        if pool_addr in IGNORED_CURVE_POOLS:
            continue
        pool_coins = []
        for coin_addr in decoded_coins_result:
            checksumed_coin_addr = to_checksum_address(coin_addr)
            if checksumed_coin_addr == ZERO_ADDRESS:
                # curve returns array of fixed length. So if current pool utilizes fewer
                # coins than the array's length, first values in the result are the real
                # coins and all addresses after are just 0x00..00
                break
            pool_coins.append(checksumed_coin_addr)

        # for metapools pool addr is the lp token as well
        pools_mapping[pool_addr] = (pool_addr, pool_coins, None)

    return pools_mapping


def query_curve_gauges(
        ethereum: 'EthereumInquirer',
        registry_contract: 'EvmContract',
        known_pools: list[ChecksumEvmAddress],
) -> dict[ChecksumEvmAddress, ChecksumEvmAddress]:
    """Queries curve gauges and returns a mapping pool address -> gauge address"""
    pools_to_gauges: dict[ChecksumEvmAddress, ChecksumEvmAddress] = {}
    for pool_address in known_pools:
        gauge_address = registry_contract.call(
            node_inquirer=ethereum,
            method_name='get_gauges',
            arguments=[pool_address],
        )[0][0]
        if gauge_address != ZERO_ADDRESS:
            pools_to_gauges[pool_address] = to_checksum_address(gauge_address)

    return pools_to_gauges
