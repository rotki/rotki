QUERY_TROVE = (
    """
    troves(
        where: {{
            owner_in: $addresses,
        }}
    ){{
        id
        debt
        owner {{
            id
        }}
        changes {{
            id
            systemStateBefore {{
                id
            }}
            systemStateAfter {{
                id
            }}
            troveOperation
            debtAfter
            debtBefore
            debtChange
            collateralAfter
            collateralBefore
            collateralChange
            borrowingFee
            transaction{{
                id
                blockNumber
                timestamp
            }}
        }}
    }}
    }}
    """
)