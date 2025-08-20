from typing import Final, Literal

from eth_typing import ABI

from rotkehlchen.types import CacheType, ChainID

BALANCER_LABEL: Final = 'Balancer'
CPT_BALANCER_V1: Final = 'balancer-v1'
CPT_BALANCER_V2: Final = 'balancer-v2'
CPT_BALANCER_V3: Final = 'balancer-v3'

BALANCER_API_CHUNK_SIZE: Final = 100
BALANCER_API_URL: Final = 'https://api-v3.balancer.fi'
CHAIN_ID_TO_BALANCER_API_MAPPINGS: Final = {
    ChainID.BASE: 'BASE',
    ChainID.GNOSIS: 'GNOSIS',
    ChainID.ETHEREUM: 'MAINNET',
    ChainID.OPTIMISM: 'OPTIMISM',
    ChainID.POLYGON_POS: 'POLYGON',
    ChainID.ARBITRUM_ONE: 'ARBITRUM',
}
BALANCER_CACHE_TYPE_MAPPING: Final = {
    CPT_BALANCER_V1: CacheType.BALANCER_V1_POOLS,
    CPT_BALANCER_V2: CacheType.BALANCER_V2_POOLS,
    CPT_BALANCER_V3: CacheType.BALANCER_V3_POOLS,
}
BALANCER_VERSION_MAPPING: Final[dict[str, Literal[1, 2, 3]]] = {
    CPT_BALANCER_V1: 1,
    CPT_BALANCER_V2: 2,
    CPT_BALANCER_V3: 3,
}

GET_POOLS_QUERY: Final = """
query GetPools($skip: Int, $first: Int, $chain: GqlChain!, $version: Int!) {
    poolGetPools(skip: $skip, first: $first, where: {chainIn: [$chain], protocolVersionIn: [$version]}) {
        id
        address
        name
        type
        symbol
        decimals
        poolTokens {
            id
            address
            symbol
            name
            weight
        }
        staking {
            gauge {
                gaugeAddress
            }
        }
    }
}
"""  # noqa: E501

GET_POOLS_COUNT_QUERY: Final = """
query GetPoolsCount($chain: GqlChain!, $version: Int!) {
    poolGetPoolsCount(where: { chainIn: [$chain], protocolVersionIn: [$version] })
}
"""


GET_POOL_PRICE_QUERY: Final = """
query GetPoolPrice($chain: GqlChain!, $poolId: String!) {
    poolGetPool(chain: $chain, id: $poolId ) {
        dynamicData {
          totalLiquidity
          totalSupply
        }
    }
}
"""


BALANCER_POOL_ABI: Final[ABI] = [
    {
        'inputs': [],
        'name': 'getPoolId',
        'outputs': [
            {
            'name': '',
            'type': 'bytes32',
            },
        ],
        'type': 'function',
    },
]
