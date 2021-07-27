MINTS_QUERY = (
    """
    mints
    (
        first: $limit,
        skip: $offset,
        where: {{
            to: $address,
            timestamp_gte: $start_ts,
            timestamp_lte: $end_ts,
        }}
    ) {{
        transaction {{
            id
        }}
        logIndex
        timestamp
        to
        pair {{
            id
            token0 {{
                id
                decimals
                name
                symbol
            }}
            token1 {{
                id
                decimals
                name
                symbol
            }}
        }}
        amount0
        amount1
        amountUSD
        liquidity
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
            sender: $address,
            timestamp_gte: $start_ts,
            timestamp_lte: $end_ts,
        }}
    ) {{
        transaction {{
            id
        }}
        logIndex
        timestamp
        sender
        pair {{
            id
            token0 {{
                id
                decimals
                name
                symbol
            }}
            token1 {{
                id
                decimals
                name
                symbol
            }}
        }}
        amount0
        amount1
        amountUSD
        liquidity
    }}}}
    """
)
