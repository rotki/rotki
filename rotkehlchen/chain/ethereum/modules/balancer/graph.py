POOLSHARES_QUERY = (
    """
    poolShares
    (
        first: $limit,
        skip: $offset,
        where: {{
            userAddress_in: $addresses,
            balance_gt: $balance,
        }}
    ) {{
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
    }}}}
    """
)
TOKENPRICES_QUERY = (
    """
    tokenPrices
    (
        first: $limit,
        skip: $offset,
        where: {{id_in: $token_ids}}
    ) {{
        id
        price
    }}}}
    """
)
SWAPS_QUERY = (
    """
    swaps
    (
        first: $limit,
        skip: $offset,
        where: {{
            userAddress_in: $addresses
            timestamp_gte: $start_ts,
            timestamp_lte: $end_ts,
        }}
        orderBy: timestamp,
        orderDirection: asc,
    ) {{
        id
        caller
        tokenIn
        tokenInSym
        tokenAmountIn
        tokenOut
        tokenOutSym
        tokenAmountOut
        poolAddress {{
            id
            tokens {{
                address
                symbol
                name
                decimals
            }}
        }}
        userAddress {{
            id
        }}
        value
        feeValue
        timestamp
    }}}}
    """
)
