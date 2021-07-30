# Get balances queries

LIQUIDITY_POSITIONS_QUERY = (
    """
    liquidityPositions
    (
        first: $limit,
        skip: $offset,
        where: {{
            user_in: $addresses,
            liquidityTokenBalance_gt: $balance,
        }}
    ) {{
        id
        liquidityTokenBalance
        pair {{
            id
            reserve0
            reserve1
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
            totalSupply
        }}
        user {{
            id
        }}
    }}}}
    """
)

# Get trades queries


V3_SWAPS_QUERY = (
    """
    swaps
    (
        first: $limit,
        skip: $offset,
        where: {{
            recipient: $address,
            timestamp_gte: $start_ts,
            timestamp_lte: $end_ts,
        }}
    ) {{
        transaction {{
            swaps {{
                id
                logIndex
                sender
                recipient
                timestamp
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
                amount0
                amount1
            }}
        }}
    }}}}
    """
)
