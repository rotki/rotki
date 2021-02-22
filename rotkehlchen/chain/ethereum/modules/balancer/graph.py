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
