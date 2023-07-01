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
            tokens {{
                address
                balance
                decimals
                denormWeight
                name
                symbol
            }}
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
ADD_LIQUIDITIES_QUERY = (
    """
    addLiquidities
    (
        first: $limit,
        skip: $offset,
        where: {{
            userAddress_in: $addresses,
            timestamp_gte: $start_ts,
            timestamp_lte: $end_ts,
        }}
        orderBy: timestamp,
        orderDirection: asc,
    ) {{
        id
        timestamp
        poolAddress {{
            id
        }}
        userAddress {{
            id
        }}
        tokenIn {{
            address
        }}
        tokenAmountIn
    }}}}
    """
)
REMOVE_LIQUIDITIES_QUERY = (
    """
    removeLiquidities
    (
        first: $limit,
        skip: $offset,
        where: {{
            userAddress_in: $addresses,
            timestamp_gte: $start_ts,
            timestamp_lte: $end_ts,
        }}
        orderBy: timestamp,
        orderDirection: asc,
    ) {{
        id
        timestamp
        poolAddress {{
            id
        }}
        userAddress {{
            id
        }}
        tokenOut {{
            address
        }}
        tokenAmountOut
    }}}}
    """
)
MINTS_QUERY = (
    """
    mints
    (
        first: $limit,
        skip: $offset,
        where: {{
            id_gte: $id,
            user_in: $addresses,
            tx_in: $transactions,
        }}
        orderBy: id,
        orderDirection: asc,
    ) {{
        id
        user {{
            id
        }}
        pool {{
            id
            tokens {{
                address
                symbol
                name
                decimals
                denormWeight
            }}
            totalWeight
        }}
        amount
    }}}}
    """
)
BURNS_QUERY = (
    """
    burns
    (
        first: $limit,
        skip: $offset,
        where: {{
            id_gte: $id,
            user_in: $addresses,
            tx_in: $transactions,
        }}
        orderBy: id,
        orderDirection: asc,
    ) {{
        id
        user {{
            id
        }}
        pool {{
            id
            tokens {{
                address
                symbol
                name
                decimals
                denormWeight
            }}
            totalWeight
        }}
        amount
    }}}}
    """
)
