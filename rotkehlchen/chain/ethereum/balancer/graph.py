# Get balances queries

# Get list of PoolShare filtering by address and balance
POOLSHARES_QUERY = """poolShares
(where: {{userAddress_in: $addresses, balance_gt: $balance}}) {{
    userAddress {{
        id
    }}
    balance
    poolId {{
        id
        symbol
        tokens {{
            address
            balance
            decimals
            denormWeight
            name
            symbol
        }}
        tokensCount
        totalShares
        totalWeight
    }}
}}}}"""

# Get list of TokenPrice by IDs
TOKENPRICES_QUERY = """tokenPrices
(where: {{id_in: $token_ids}}) {{
    id
    price
}}}}
"""

# Get history queries
# TODO: explore how to integrate pagination and edges in the queries below
# Get list of Swap filtering by address
SWAPS_QUERY = """swaps
(orderBy: timestamp, where: {{userAddress: $address}}) {{
    id
    caller
    tokenIn
    tokenInSym
    tokenOut
    tokenOutSym
    tokenAmountIn
    tokenAmountOut
    poolAddress {{
      id
      name
    }}
    value
    feeValue
    poolTotalSwapVolume
    poolTotalSwapFee
    poolLiquidity
    timestamp
}}}}
"""

# Get list of Swap filtering by address and timestamp (gte).
SWAPS_QUERY_FILTERING_BY_TS_GTE = """swaps
(orderBy: timestamp, where: {{userAddress: $address, timestamp_gte: $timestamp}}) {{
    id
    caller
    tokenIn
    tokenInSym
    tokenOut
    tokenOutSym
    tokenAmountIn
    tokenAmountOut
    poolAddress {{
      id
      name
    }}
    value
    feeValue
    poolTotalSwapVolume
    poolTotalSwapFee
    poolLiquidity
    timestamp
}}}}
"""
