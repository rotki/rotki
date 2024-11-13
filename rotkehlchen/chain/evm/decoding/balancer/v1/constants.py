USER_GET_POOL_BALANCES_QUERY = """
query UserGetPoolBalances($address: String, $chain: GqlChain!) {
    userGetPoolBalances(address: $address, chains: [$chain]) {
        chain
        poolId
        stakedBalance
        tokenAddress
        tokenPrice
        totalBalance
        walletBalance
    }
}
"""
