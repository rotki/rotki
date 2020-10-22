# ! TODO VN PR: GraphQL query
# ! * Address query processing in graph.py for avoiding unclosed "}"
# ! * Triple quotes require .format()
# ! * Pagination
# ! * Consider fetching USD price per token
# Get list of PoolShare filtering by address and balance
POOLSHARES_QUERY = """poolShares
(where: {{userAddress_in: $addresses, balance_gt: $balance}}) {{
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
            denormWeight
            name
            symbol
        }}
        tokensCount
        totalShares
        totalWeight
    }}
}}}}"""

# Get list of TokenPrice by IDs
TOKENPRICES_QUERY = """tokenPrices
(where: {{id_in: $token_ids}}) {{
    id
    price
}}}}
"""
