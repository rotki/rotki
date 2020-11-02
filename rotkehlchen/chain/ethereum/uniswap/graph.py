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
        }}) {{
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

TOKEN_DAY_DATAS_QUERY = (
    """
    tokenDayDatas
    (
        first: $limit,
        skip: $offset,
        where: {{
            token_in: $token_ids,
            date: $datetime,
        }}) {{
        date
        token {{
            id
        }}
        priceUSD
    }}}}
    """
)
