from typing import Final

from rotkehlchen.types import ChainID

BALANCER_LABEL = 'Balancer'
CPT_BALANCER_V1: Final = 'balancer-v1'
CPT_BALANCER_V2: Final = 'balancer-v2'

BALANCER_API_CHUNK_SIZE: Final = 100
BALANCER_API_URL: Final = 'https://api-v3.balancer.fi'
CHAIN_ID_TO_BALANCER_API_MAPPINGS = {
    ChainID.BASE: 'BASE',
    ChainID.GNOSIS: 'GNOSIS',
    ChainID.ETHEREUM: 'MAINNET',
    ChainID.OPTIMISM: 'OPTIMISM',
    ChainID.POLYGON_POS: 'POLYGON',
    ChainID.ARBITRUM_ONE: 'ARBITRUM',
}

GET_POOLS_QUERY = """
query GetPools($skip: Int, $first: Int, $chain: GqlChain!, $version: Int!) {
    poolGetPools(skip: $skip, first: $first, where: {chainIn: [$chain], protocolVersionIn: [$version]}) {
        id
        address
        name
        type
        symbol
        decimals
        displayTokens {
            id
            address
            symbol
            name
            weight
        }
    }
}
"""  # noqa: E501

GET_POOLS_COUNT_QUERY = """
query GetPoolsCount($chain: GqlChain!, $version: Int!) {
    poolGetPoolsCount(where: { chainIn: [$chain], protocolVersionIn: [$version] })
}
"""


GET_V1_POOL_PRICE_QUERY = """
query GetPoolPrice($chain: GqlChain!, $poolId: String!) {
    poolGetPool(chain: $chain, id: $poolId ) {
        dynamicData {
          totalLiquidity
          totalSupply
        }
    }
}
"""
