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
            id_gt: $id,
        }}
    ) {{
        id
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
            id_gt: $id,
        }}
    ) {{
        id
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


TOKEN_DAY_DATAS_QUERY = (
    """
    tokenDayDatas
    (
        first: $limit,
        skip: $offset,
        where: {{
            token_in: $token_ids,
            date: $datetime,
        }}
    ) {{
        date
        token {{
            id
        }}
        priceUSD
    }}}}
    """
)

LIQUIDITY_POSITIONS_QUERY = (
    """
    liquidityPositions
    (
        first: $limit,
        skip: $offset,
        where: {{
            user_in: $addresses,
            liquidityTokenBalance_gt: $balance,
            id_gt: $id,
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
