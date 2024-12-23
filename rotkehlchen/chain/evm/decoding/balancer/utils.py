import logging
from typing import TYPE_CHECKING, Any, Literal

import requests

from rotkehlchen.chain.evm.decoding.balancer.constants import (
    BALANCER_API_CHUNK_SIZE,
    BALANCER_API_URL,
    BALANCER_POOL_ABI,
    CHAIN_ID_TO_BALANCER_API_MAPPINGS,
    GET_POOL_PRICE_QUERY,
    GET_POOLS_COUNT_QUERY,
    GET_POOLS_QUERY,
)
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_int
from rotkehlchen.types import Price

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChainID

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


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


def query_balancer_pools_count(chain: 'ChainID', version: Literal[1, 2]) -> int:
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


def query_balancer_pools(chain: 'ChainID', version: Literal[1, 2]) -> list[dict[str, Any]]:
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


def get_balancer_pool_price(
        pool_token: 'EvmToken',
        evm_inquirer: 'EvmNodeInquirer',
) -> Price:
    """Get price for a Balancer pool token
    May raise:
    - RemoteError
    """
    pool_id = evm_inquirer.call_contract(
        abi=BALANCER_POOL_ABI,
        method_name='getPoolId',
        contract_address=pool_token.evm_address,
    )
    data = query_balancer_api(
        query=GET_POOL_PRICE_QUERY,
        variables={
            'chain': CHAIN_ID_TO_BALANCER_API_MAPPINGS[pool_token.chain_id],
            'poolId': '0x' + pool_id.hex(),
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
