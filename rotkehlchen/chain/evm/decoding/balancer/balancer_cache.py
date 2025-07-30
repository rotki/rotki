import logging
from typing import TYPE_CHECKING, Literal

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.evm.decoding.balancer.constants import (
    CPT_BALANCER_V1,
)
from rotkehlchen.chain.evm.decoding.balancer.utils import (
    query_balancer_pools,
    query_balancer_pools_count,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.misc import ONE
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import (
    globaldb_get_general_cache_values,
    globaldb_set_general_cache_values,
    globaldb_update_cache_last_ts,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address, deserialize_int
from rotkehlchen.types import CacheType, ChainID, ChecksumEvmAddress, TokenKind

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def query_balancer_data(
        version: Literal[1, 2],
        inquirer: 'EvmNodeInquirer',
        msg_aggregator: 'MessagesAggregator',
        protocol: Literal['balancer-v1', 'balancer-v2'],
        cache_type: Literal[CacheType.BALANCER_V1_POOLS, CacheType.BALANCER_V2_POOLS],
        reload_all: bool,
) -> tuple[set['ChecksumEvmAddress'], set['ChecksumEvmAddress']]:
    """Query and store balancer pools with their gauges.

    May raise:
    - RemoteError
    """
    globaldb = GlobalDBHandler()
    latest_pools_count = query_balancer_pools_count(
        chain=inquirer.chain_id,
        version=version,
    )
    pool_key_parts = ((str_chain_id := str(inquirer.chain_id.value)),)
    if reload_all is False:
        with globaldb.conn.read_ctx() as cursor:
            existing_pools = {
                string_to_evm_address(address)
                for address in globaldb_get_general_cache_values(
                    cursor=cursor,
                    key_parts=(cache_type, *pool_key_parts),
                )
            }
            gauge_cache_type: Literal[CacheType.BALANCER_V1_GAUGES, CacheType.BALANCER_V2_GAUGES] = CacheType.BALANCER_V1_GAUGES if version == 1 else CacheType.BALANCER_V2_GAUGES  # noqa: E501
            existing_gauges = {
                string_to_evm_address(address)
                for address in globaldb_get_general_cache_values(
                    cursor=cursor,
                    key_parts=(gauge_cache_type, str_chain_id),
                )
            }

        if latest_pools_count == len(existing_pools):
            with globaldb.conn.write_ctx() as write_cursor:
                globaldb_update_cache_last_ts(
                    write_cursor=write_cursor,
                    key_parts=pool_key_parts,
                    cache_type=cache_type,
                )

            return existing_pools, existing_gauges

    pools, gauges = set(), set()
    pool_tokens_to_update = []
    token_encounter_info = TokenEncounterInfo(
        description=f'Querying {inquirer.chain_name} {protocol} balances',
        should_notify=False,
    )
    for pool in query_balancer_pools(chain=inquirer.chain_id, version=version):
        try:
            underlying_tokens = [token for token in pool['poolTokens'] if pool['address'] != token['address']]  # noqa: E501
            default_weight = ONE / len(underlying_tokens)
            pool_token = get_or_create_evm_token(
                userdb=inquirer.database,
                chain_id=inquirer.chain_id,
                protocol=protocol,
                name=pool['name'].strip(),  # API responses sometimes contain trailing/leading whitespace in pool names and symbols  # noqa: E501
                symbol=pool['symbol'].strip(),
                decimals=deserialize_int(pool['decimals']),
                evm_address=deserialize_evm_address(pool['address']),
                encounter=token_encounter_info,
                underlying_tokens=[
                    UnderlyingToken(
                        address=get_or_create_evm_token(
                            userdb=inquirer.database,
                            chain_id=inquirer.chain_id,
                            evm_address=deserialize_evm_address(token['address']),
                            encounter=token_encounter_info,
                        ).evm_address,
                        token_kind=TokenKind.ERC20,
                        weight=FVal(token['weight']) if token.get('weight') is not None else default_weight,  # noqa: E501
                    )
                    for token in underlying_tokens
                ],
            )
            pools.add(pool_token.evm_address)
            if (gauge_address := ((pool.get('staking') or {}).get('gauge') or {}).get('gaugeAddress')) is not None:  # noqa: E501
                gauges.add(deserialize_evm_address(gauge_address))

            if pool_token.protocol != CPT_BALANCER_V1:
                pool_tokens_to_update.append(pool_token)
        except (KeyError, ValueError, TypeError, DeserializationError) as e:
            msg = f'missing key {e!s}' if isinstance(e, KeyError) else str(e)
            log.error(
                f'Failed to process {protocol} pool on {inquirer.chain_name} due to {msg}. '
                f'Pool: {pool}. Skipping...',
            )
            continue

    if pool_tokens_to_update:
        log.debug(f'Updating protocol for {len(pool_tokens_to_update)} {inquirer.chain_name} {protocol} assets')  # noqa: E501
        globaldb.set_tokens_protocol_if_missing(
            tokens=pool_tokens_to_update,
            new_protocol=CPT_BALANCER_V1,
        )

    with globaldb.conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(cache_type, *pool_key_parts),
            values=pools,
        )
        if len(gauges) > 0:
            gauge_cache_type = CacheType.BALANCER_V1_GAUGES if version == 1 else CacheType.BALANCER_V2_GAUGES  # noqa: E501
            globaldb_set_general_cache_values(
                write_cursor=write_cursor,
                key_parts=(gauge_cache_type, str_chain_id),
                values=gauges,
            )

        globaldb_update_cache_last_ts(
            write_cursor=write_cursor,
            cache_type=cache_type,
            key_parts=pool_key_parts,
        )

    return pools, gauges


def read_balancer_pools_and_gauges_from_cache(
        chain_id: ChainID,
        version: Literal['1', '2'],
        cache_type: Literal[CacheType.BALANCER_V1_POOLS, CacheType.BALANCER_V2_POOLS],
) -> tuple[set[ChecksumEvmAddress], set[ChecksumEvmAddress]]:
    """Retrieves cached balancer pool and gauge addresses for a given chain and version.

    Returns:
        - Set of pool addresses
        - Set of gauge addresses
    """
    with GlobalDBHandler().conn.read_ctx() as cursor:
        pool_addresses = {
            string_to_evm_address(pool_address)
            for pool_address in globaldb_get_general_cache_values(
                cursor=cursor,
                key_parts=(cache_type, str(chain_id.value)),
            )
        }

        gauge_cache_type: Literal[CacheType.BALANCER_V1_GAUGES, CacheType.BALANCER_V2_GAUGES] = CacheType.BALANCER_V1_GAUGES if version == '1' else CacheType.BALANCER_V2_GAUGES  # noqa: E501
        gauge_addresses = {
            string_to_evm_address(gauge_address)
            for gauge_address in globaldb_get_general_cache_values(
                cursor=cursor,
                key_parts=(gauge_cache_type, str(chain_id.value)),
            )
        }

    return pool_addresses, gauge_addresses
