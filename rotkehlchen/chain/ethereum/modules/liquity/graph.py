QUERY_TROVE = (
    """
    troves(
        where: {
            owner_in: $addresses,
        }
    ){
        id
        debt
        owner {
            id
        }
        changes(orderBy: sequenceNumber){
            id
            systemStateBefore {
                id
            }
            systemStateAfter {
                id
            }
            troveOperation
            debtAfter
            debtBefore
            debtChange
            collateralAfter
            collateralBefore
            collateralChange
            sequenceNumber
            borrowingFee
            transaction{
                id
                blockNumber
                sequenceNumber
                timestamp
            }
        }
    }
    }
    """
)

QUERY_STAKE = (
    """
        lqtyStakes(
            where: {
                id_in: $addresses,
            }
        ){
            id
            amount
            changes(orderBy: sequenceNumber){
                transaction {
                    id
                    sequenceNumber
                    timestamp
                }
                stakeOperation
                stakedAmountAfter
                stakedAmountChange
                issuanceGain
                redemptionGain
            }
        }
    }
    """
)
