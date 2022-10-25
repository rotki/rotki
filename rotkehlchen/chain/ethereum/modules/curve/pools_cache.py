from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

from eth_utils import to_checksum_address

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.constants import ZERO_ADDRESS
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants import ONE
from rotkehlchen.constants.ethereum import (
    CURVE_ADDRESS_PROVIDER,
    CURVE_METAPOOL_FACTORY_ABI,
    CURVE_REGISTRY_ABI,
    ETH_SPECIAL_ADDRESS,
)
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.globaldb import GlobalDBHandler
from rotkehlchen.types import (
    CURVE_POOL_PROTOCOL,
    ChainID,
    ChecksumEvmAddress,
    EvmTokenKind,
    GeneralCacheType,
)
from rotkehlchen.utils.misc import hex_or_bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager


CURVE_POOLS_MAPPING_TYPE = Dict[
    ChecksumEvmAddress,  # lp token address
    Tuple[
        ChecksumEvmAddress,  # pool address
        List[ChecksumEvmAddress],  # list of coins addresses
        Optional[List[ChecksumEvmAddress]],  # optional list of underlying coins addresses
    ],
]


def clear_curve_pools_cache(write_cursor: DBCursor) -> None:
    """Clears all curve pools related cache entries in the globaldb.
    Doesn't raise anything unless cache entries were inserted incorrectly."""
    curve_lp_tokens = GlobalDBHandler().get_general_cache_values(
        key_parts=[GeneralCacheType.CURVE_LP_TOKENS],
    )
    for lp_token in curve_lp_tokens:
        pool_addr = GlobalDBHandler().get_general_cache_values(
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, lp_token],
        )[0]
        GlobalDBHandler().delete_general_cache(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_TOKENS, pool_addr],
        )
        GlobalDBHandler().delete_general_cache(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, lp_token],
        )
    GlobalDBHandler().delete_general_cache(
        write_cursor=write_cursor,
        key_parts=[GeneralCacheType.CURVE_LP_TOKENS],
    )


def read_curve_pools() -> Set[ChecksumEvmAddress]:
    """Reads globaldb cache and returns a set of all known curve pools' addresses.
    Doesn't raise anything unless cache entries were inserted incorrectly."""
    curve_pools_lp_tokens = GlobalDBHandler().get_general_cache_values(
        key_parts=[GeneralCacheType.CURVE_LP_TOKENS],
    )
    curve_pools = set()
    for lp_token_addr in curve_pools_lp_tokens:
        pool_addr = GlobalDBHandler().get_general_cache_values(
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, lp_token_addr],
        )[0]
        curve_pools.add(string_to_evm_address(pool_addr))
    return curve_pools


def ensure_curve_tokens_existence(
        ethereum_manager: 'EthereumManager',
        pools_mapping: CURVE_POOLS_MAPPING_TYPE,
) -> None:
    """This function receives data about curve pools and ensures that lp tokens and pool coins
    exist in rotki's database."""
    for lp_token_address, pool_info in pools_mapping.items():
        _, coins, underlying_coins = pool_info
        # ensure lp token exists in the globaldb
        get_or_create_evm_token(
            userdb=ethereum_manager.database,
            evm_address=lp_token_address,
            chain=ChainID.ETHEREUM,
            ethereum_manager=ethereum_manager,
            protocol=CURVE_POOL_PROTOCOL,
        )

        # Ensure pool coins exist in the globaldb.
        # We have to create underlying tokens only if pool utilizes them.
        if underlying_coins is None or underlying_coins == coins:
            # If underlying coins is None, it means that pool doesn't utilize them.
            # If underlying coins list is equal to coins then there are no underlying coins as well.  # noqa: E501
            for token_address in coins:
                if token_address == ETH_SPECIAL_ADDRESS:
                    continue
                # ensure token exists
                get_or_create_evm_token(
                    userdb=ethereum_manager.database,
                    evm_address=token_address,
                    chain=ChainID.ETHEREUM,
                    ethereum_manager=ethereum_manager,
                )
        else:
            # Otherwise, coins and underlying coins lists represent a
            # mapping coin - underlying coin (each coin always has one underlying coin).
            for token_address, underlying_token_address in zip(coins, underlying_coins):
                if token_address == ETH_SPECIAL_ADDRESS:
                    continue
                # ensure underlying token exists
                get_or_create_evm_token(
                    userdb=ethereum_manager.database,
                    evm_address=underlying_token_address,
                    chain=ChainID.ETHEREUM,
                    ethereum_manager=ethereum_manager,
                )
                # and ensure token exists
                get_or_create_evm_token(
                    userdb=ethereum_manager.database,
                    evm_address=token_address,
                    chain=ChainID.ETHEREUM,
                    ethereum_manager=ethereum_manager,
                    underlying_tokens=[UnderlyingToken(
                        address=underlying_token_address,
                        token_kind=EvmTokenKind.ERC20,
                        weight=ONE,
                    )],
                )


def save_curve_pools_to_cache(
        write_cursor: DBCursor,
        pools_mapping: CURVE_POOLS_MAPPING_TYPE,
) -> None:
    """Receives data about curve pools and saves lp tokens, pool addresses and
    pool coins in cache."""
    GlobalDBHandler().set_general_cache_values(
        write_cursor=write_cursor,
        key_parts=[GeneralCacheType.CURVE_LP_TOKENS],
        values=pools_mapping.keys(),  # keys of pools_mapping are lp tokens
    )
    for lp_token_address, pool_info in pools_mapping.items():
        pool_address, coins, _underlying_coins = pool_info
        GlobalDBHandler().set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, lp_token_address],
            values=[pool_address],
        )
        GlobalDBHandler().set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_TOKENS, pool_address],
            values=coins,
        )


def update_curve_registry_pools_cache(
        write_cursor: DBCursor,
        ethereum_manager: 'EthereumManager',
) -> None:
    """Query pools from curve registry.
    May raise:
    - RemoteError if failed to query etherscan or node
    - NotERC20Conformant if failed to query info while calling get_or_create_evm_token
    """
    get_registry_result = CURVE_ADDRESS_PROVIDER.call(
        manager=ethereum_manager,
        method_name='get_registry',
    )
    registry_address = to_checksum_address(get_registry_result)
    registry_contract = EvmContract(
        address=registry_address,
        abi=CURVE_REGISTRY_ABI,
        deployed_block=0,  # deployment_block is not used and the contract is dynamic
    )
    registry_pool_count = registry_contract.call(
        manager=ethereum_manager,
        method_name='pool_count',
    )
    registry_pools_result = ethereum_manager.multicall_specific(
        contract=registry_contract,
        method_name='pool_list',
        arguments=[(x,) for x in range(registry_pool_count)],
        decode_result=False,  # don't decode since decoding unchecksums address
    )
    pool_addresses = []
    for pool_addr_encoded in registry_pools_result:
        decoded_pool_addr = hex_or_bytes_to_address(pool_addr_encoded)  # already checksumed
        pool_addresses.append(decoded_pool_addr)

    registry_lp_tokens_result = ethereum_manager.multicall_specific(
        contract=registry_contract,
        method_name='get_lp_token',
        arguments=[(x,) for x in pool_addresses],
        decode_result=False,  # don't decode since decoding unchecksums address
    )
    registry_coins_result = ethereum_manager.multicall_specific(
        contract=registry_contract,
        method_name='get_coins',
        arguments=[(x,) for x in pool_addresses],
    )
    registry_underlying_coins_result = ethereum_manager.multicall_specific(
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

    ensure_curve_tokens_existence(ethereum_manager=ethereum_manager, pools_mapping=pools_mapping)
    save_curve_pools_to_cache(write_cursor=write_cursor, pools_mapping=pools_mapping)


def update_curve_metapools_cache(
        write_cursor: DBCursor,
        ethereum_manager: 'EthereumManager',
) -> None:
    """Query pools from curve metapool factory.
    May raise:
    - RemoteError if failed to query etherscan or node
    - NotERC20Conformant if failed to query info while calling get_or_create_evm_token
    """
    factory_address_result = CURVE_ADDRESS_PROVIDER.call(
        manager=ethereum_manager,
        method_name='get_address',
        arguments=[3],  # 3 is metapool factory id
    )
    factory_address = to_checksum_address(factory_address_result)
    factory_contract = EvmContract(
        address=factory_address,
        abi=CURVE_METAPOOL_FACTORY_ABI,
        deployed_block=0,  # deployment_block is not used and the contract is dynamic
    )
    pool_count = factory_contract.call(
        manager=ethereum_manager,
        method_name='pool_count',
    )
    pool_addrs_result = ethereum_manager.multicall_specific(
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
    pool_coins_result = ethereum_manager.multicall_specific(
        contract=factory_contract,
        method_name='get_coins',
        arguments=[(x,) for x in pool_addresses],
    )
    pools_mapping: CURVE_POOLS_MAPPING_TYPE = {}
    for pool_addr, (decoded_coins_result,) in zip(pool_addresses, pool_coins_result):
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

    ensure_curve_tokens_existence(ethereum_manager=ethereum_manager, pools_mapping=pools_mapping)
    save_curve_pools_to_cache(write_cursor=write_cursor, pools_mapping=pools_mapping)
