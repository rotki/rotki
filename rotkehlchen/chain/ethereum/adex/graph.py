BONDS_QUERY = (
    """
    bonds
    (
        first: $limit,
        skip: $offset,
        where: {{
            owner_in: $user_identities,
        }}
    ) {{
        id
        owner
        poolId
        timestamp
        amount
        nonce
    }}}}
    """
)
UNBONDS_QUERY = (
    """
    unbonds
    (
        first: $limit,
        skip: $offset,
        where: {{
            owner_in: $user_identities,
        }}
    ) {{
        id
        bondId
        owner
        timestamp
    }}}}
    """
)
UNBOND_REQUESTS_QUERY = (
    """
    unbondRequests
    (
        first: $limit,
        skip: $offset,
        where: {{
            owner_in: $user_identities,
        }}
    ) {{
        id
        bondId
        owner
        timestamp
    }}}}
    """
)
