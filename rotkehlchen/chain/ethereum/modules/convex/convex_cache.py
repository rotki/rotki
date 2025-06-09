import logging
from typing import TYPE_CHECKING, Literal

from rotkehlchen.chain.ethereum.modules.convex.constants import BOOSTER
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.globaldb.cache import (
    globaldb_get_general_cache_values,
    globaldb_get_unique_cache_value,
    globaldb_set_general_cache_values,
    globaldb_set_unique_cache_value,
    globaldb_update_cache_last_ts,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def get_existing_pools(
        cursor: 'DBCursor',
        cache_type: Literal[CacheType.CONVEX_POOL_ADDRESS],
) -> set[ChecksumEvmAddress]:
    """Returns all the convex pool rewards address stored in cache"""
    return {
        string_to_evm_address(address) for address in globaldb_get_general_cache_values(
            cursor=cursor,
            key_parts=(cache_type,),
        )
    }


def read_convex_data_from_cache() -> tuple[dict[ChecksumEvmAddress, str]]:
    """Reads convex pools and names from global db cache tables."""
    pools: dict[ChecksumEvmAddress, str] = {}
    with GlobalDBHandler().conn.read_ctx() as cursor:
        for pool_address in get_existing_pools(
            cursor=cursor,
            cache_type=CacheType.CONVEX_POOL_ADDRESS,
        ):
            if (pool_name := globaldb_get_unique_cache_value(
                cursor=cursor,
                key_parts=(CacheType.CONVEX_POOL_NAME, pool_address),
            )) is None:
                continue
            pools[pool_address] = pool_name

    return (pools,)


def query_convex_data_from_chain(
        ethereum: 'EthereumInquirer',
        existing_pools: set[ChecksumEvmAddress],
) -> dict[ChecksumEvmAddress, str]:
    """
    Query Booster contract and fetch all reward pools. It creates a mapping for convex pools
    to the symbol of the underlying lp token. It uses the `existing_pools` argument to ensure
    that additional queries are not made for pools that are already cached.

    May raise:
    - RemoteError if failed to query chain
    """
    booster_contract = ethereum.contracts.contract(BOOSTER)
    pools_count = booster_contract.call(node_inquirer=ethereum, method_name='poolLength')

    calls_to_booster = [(
        booster_contract.address,
        booster_contract.encode('poolInfo', [x]),
    ) for x in range(len(existing_pools), pools_count)]
    if len(booster_result := ethereum.multicall(calls=calls_to_booster)) == 0:
        return {}

    convex_rewards_addrs: list[ChecksumEvmAddress] = []
    convex_lp_tokens_addrs = []
    for single_booster_result in booster_result:
        crv_rewards = bytes_to_address(single_booster_result[96:128])
        lp_token_addr = bytes_to_address(single_booster_result[0:32])
        convex_rewards_addrs.append(crv_rewards)
        convex_lp_tokens_addrs.append(lp_token_addr)

    lp_tokens_contract = EvmContract(  # only need it to encode and decode
        address=ZERO_ADDRESS,
        abi=ethereum.contracts.abi('CONVEX_LP_TOKEN'),
        deployed_block=0,
    )
    calls_to_lp_tokens = [(lp_token_addr, lp_tokens_contract.encode('symbol')) for lp_token_addr in convex_lp_tokens_addrs]  # noqa: E501
    lp_tokens_result = ethereum.multicall(calls=calls_to_lp_tokens)

    queried_convex_pools_info: dict[ChecksumEvmAddress, str] = {}
    for convex_reward_addr, single_lp_token_result in zip(convex_rewards_addrs, lp_tokens_result, strict=True):  # length should be equal # noqa: E501
        decoded_lp_token_symbol = lp_tokens_contract.decode(single_lp_token_result, 'symbol')[0]
        queried_convex_pools_info[convex_reward_addr] = decoded_lp_token_symbol

    return queried_convex_pools_info


def query_convex_data(
        inquirer: 'EthereumInquirer',
        cache_type: Literal[CacheType.CONVEX_POOL_ADDRESS],
        msg_aggregator: 'MessagesAggregator',  # pylint: disable=unused-argument  # argument is unused to keep the interface consistent with the other functions because they all are called similarly in ensure_cache_data_is_updated and refresh_general_cache
        reload_all: bool,  # pylint: disable=unused-argument
) -> dict[ChecksumEvmAddress, str] | None:
    """
    Queries chain for all convex rewards pools and returns a list of the mappings not cached

    May raise:
    - RemoteError if failed to query chain
    """
    with GlobalDBHandler().conn.read_ctx() as cursor:
        existing_pools = get_existing_pools(cursor=cursor, cache_type=cache_type)

    try:
        convex_pools = query_convex_data_from_chain(
            ethereum=inquirer,
            existing_pools=existing_pools,
        )
    except RemoteError as err:
        log.error(f'Could not query chain for convex pools due to: {err}')
        return None

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        for pool_address, pool_name in convex_pools.items():
            globaldb_set_general_cache_values(
                write_cursor=write_cursor,
                key_parts=(CacheType.CONVEX_POOL_ADDRESS,),
                values=[pool_address],
            )
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=(CacheType.CONVEX_POOL_NAME, pool_address),
                value=pool_name,
            )

        globaldb_update_cache_last_ts(  # update the last_queried_ts of db entries
            write_cursor=write_cursor,
            cache_type=cache_type,
            key_parts=None,
        )

    return convex_pools
