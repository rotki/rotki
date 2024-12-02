import logging
from typing import TYPE_CHECKING, Any, Literal

import requests
from eth_utils import to_checksum_address

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.evm.decoding.balancer.constants import (
    BALANCER_API_CHUNK_SIZE,
    BALANCER_API_URL,
    CHAIN_ID_TO_BALANCER_API_MAPPINGS,
    CPT_BALANCER_V1,
    GET_POOL_PRICE_QUERY,
    GET_POOLS_COUNT_QUERY,
    GET_POOLS_QUERY,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value_at_ts,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_int
from rotkehlchen.types import CacheType, EvmTokenKind, Price
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChainID

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def query_balancer_data(
        version: Literal[1, 2],
        inquirer: 'EvmNodeInquirer',
        protocol: Literal['balancer-v1', 'balancer-v2'],
        cache_type: Literal[CacheType.BALANCER_V1_POOLS, CacheType.BALANCER_V2_POOLS],
) -> None:
    """Query and store balancer pools.
    May raise:
    - RemoteError
    """
    latest_pools_count = _query_balancer_pools_count(
        chain=inquirer.chain_id,
        version=version,
    )
    cache_key_parts = (cache_type, str(inquirer.chain_id.value), str(version))
    now = ts_now()
    with GlobalDBHandler().conn.read_ctx() as cursor:
        if (saved_pools_count_str := globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=cache_key_parts,
        )) is None:
            saved_pools_count = 0
        else:
            saved_pools_count = int(saved_pools_count_str)

    if latest_pools_count == saved_pools_count:
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            globaldb_set_unique_cache_value_at_ts(
                write_cursor=write_cursor,
                key_parts=cache_key_parts,
                value=str(latest_pools_count),
                timestamp=now,
            )
            return None

    for pool in _query_balancer_pools(chain=inquirer.chain_id, version=version):
        try:
            pool_token = get_or_create_evm_token(
                userdb=inquirer.database,
                chain_id=inquirer.chain_id,
                protocol=protocol,
                name=pool['name'].strip(),
                symbol=pool['symbol'].strip(),
                decimals=deserialize_int(pool['decimals']),
                evm_address=string_to_evm_address(to_checksum_address(pool['address'])),
                encounter=TokenEncounterInfo(
                    description=f'Querying {inquirer.chain_name} {protocol} balances',
                    should_notify=False,
                ),
                underlying_tokens=[
                    UnderlyingToken(
                        address=get_or_create_evm_token(
                            userdb=inquirer.database,
                            chain_id=inquirer.chain_id,
                            protocol=protocol,
                            name=token['name'].strip(),
                            symbol=token['symbol'].strip(),
                            evm_address=string_to_evm_address(to_checksum_address(token['address'])),
                            encounter=TokenEncounterInfo(
                                description=f'Querying {inquirer.chain_name} {protocol} balances',
                                should_notify=False,
                            ),
                        ).evm_address,
                        token_kind=EvmTokenKind.ERC20,
                        weight=FVal(token['weight']),
                    )
                    for token in pool['displayTokens']
                ],
            )
        except (KeyError, ValueError, TypeError, DeserializationError) as e:
            msg = f'missing key {e!s}' if isinstance(e, KeyError) else str(e)
            log.error(
                f'Failed to process {protocol} pool on {inquirer.chain_name} due to {msg}. '
                f'Pool: {pool}. Skipping...',
            )
            continue

        if pool_token.protocol != CPT_BALANCER_V1:
            log.debug(f'Updating protocol for {inquirer.chain_name} {protocol} asset {pool_token}')
            GlobalDBHandler.set_token_protocol_if_missing(
                token=pool_token,
                new_protocol=CPT_BALANCER_V1,
            )

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_unique_cache_value_at_ts(
            write_cursor=write_cursor,
            key_parts=cache_key_parts,
            value=str(latest_pools_count),
            timestamp=now,
        )


def query_balancer_api(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    """Make a request to Balancer API with standardized error handling.
    Raises:
    - RemoteError: If the request fails or response is invalid
    """
    try:
        response = requests.post(
            url=BALANCER_API_URL,
            json={
                'query': query,
                'variables': variables,
            },
            timeout=CachedSettings().get_timeout_tuple(),
        )
        if response.status_code != 200:
            raise RemoteError(f'Balancer API request failed with status {response.status_code}')

        if 'errors' in (data := response.json()):
            raise RemoteError(f"Balancer API query failed: {data['errors']}")

        return data['data']
    except (requests.exceptions.RequestException, KeyError) as e:
        msg = f'missing key {e!s}' if isinstance(e, KeyError) else str(e)
        raise RemoteError(f'Balancer API request with query={query} and vars={variables} failed due to {msg}') from e  # noqa: E501


def _query_balancer_pools_count(chain: 'ChainID', version: Literal[1, 2]) -> int:
    """Fetch the total number of balancer pools for the specified chain and protocol
    May raise:
    - RemoteError
    """
    data = query_balancer_api(
        query=GET_POOLS_COUNT_QUERY,
        variables={
            'chain': CHAIN_ID_TO_BALANCER_API_MAPPINGS[chain],
            'version': version,
        },
    )
    try:
        return deserialize_int(data['poolGetPoolsCount'])
    except (DeserializationError, KeyError) as e:
        msg = f'missing key {e!s}' if isinstance(e, KeyError) else str(e)
        raise RemoteError(f'Balancer v{version} pools count query for {chain} failed due to {msg}') from e  # noqa: E501


def _query_balancer_pools(chain: 'ChainID', version: Literal[1, 2]) -> list[dict[str, Any]]:
    """Fetches and processes balancer pools from API.
    May raise:
    - RemoteError
    """
    offset, all_pools = 0, []
    while True:
        data = query_balancer_api(
            query=GET_POOLS_QUERY,
            variables={
                'skip': offset,
                'version': version,
                'first': BALANCER_API_CHUNK_SIZE,
                'chain': CHAIN_ID_TO_BALANCER_API_MAPPINGS[chain],
            },
        )
        try:
            all_pools.extend(pools_chunk := data['poolGetPools'])
        except KeyError as e:
            raise RemoteError(f'Balancer v{version} pools query for {chain} failed due to missing key {e!s}') from e  # noqa: E501

        if len(pools_chunk) < BALANCER_API_CHUNK_SIZE:
            break

        offset += BALANCER_API_CHUNK_SIZE

    return all_pools


def get_balancer_pool_price(pool_token: 'EvmToken') -> Price:
    """Get price for a Balancer pool token
    May raise:
    - RemoteError
    """
    data = query_balancer_api(
        query=GET_POOL_PRICE_QUERY,
        variables={
            'chain': CHAIN_ID_TO_BALANCER_API_MAPPINGS[pool_token.chain_id],
            'poolId': pool_token.evm_address,
        },
    )
    try:
        pool_data = data['poolGetPool']['dynamicData']
        total_liquidity = FVal(pool_data['totalLiquidity'])
        total_supply = FVal(pool_data['totalSupply'])
        return Price(total_liquidity / total_supply)
    except (ValueError, KeyError) as e:
        msg = f'missing key {e!s}' if isinstance(e, KeyError) else str(e)
        raise RemoteError(
            f'Balancer pool price for {pool_token.evm_address} query '
            f'on {pool_token.chain_id.to_name()} failed due to {msg}',
        ) from e
