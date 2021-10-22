# Get trades queries


V3_SWAPS_QUERY = (
    """
    swaps
    (
        first: $limit,
        skip: $offset,
        where: {{
            origin: $address,
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
