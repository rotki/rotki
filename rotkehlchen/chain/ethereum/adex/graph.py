BONDS_QUERY = (
    """
    bonds
    (
        first: $limit,
        skip: $offset,
        where: {{
            owner_in: $user_identities,
            timestamp_gte: $start_ts,
            timestamp_lte: $end_ts,
        }}
    ) {{
        id
        owner
        poolId
        timestamp
        amount
        nonce
        slashedAtStart
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
            timestamp_gte: $start_ts,
            timestamp_lte: $end_ts,
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
            timestamp_gte: $start_ts,
            timestamp_lte: $end_ts,
        }}
    ) {{
        id
        bondId
        owner
        timestamp
        willUnlock
    }}}}
    """
)
