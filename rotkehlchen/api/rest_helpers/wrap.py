from rotkehlchen.fval import FVal


def calculate_wrap_score(
        num_of_trades: int,
        num_of_transactions: int,
        num_of_chains: int,
        eth_spent_on_gas: FVal,
        gnosis_user: bool,
) -> int:
    """This logic will be delete once we remove the wrap

    Example score for yabir: 62 * 25 + 3 * 3600 + 7 * 50 + 0.217 * 1500 + 1000 = 14025
    """
    trades_score = 25
    transactions_score = 3
    num_of_chains_score = 50
    gas_score = 1500
    gnosis_boost = 1000 if gnosis_user is True else 0
    return FVal(
        num_of_trades * trades_score +
        num_of_transactions * transactions_score +
        num_of_chains * num_of_chains_score +
        eth_spent_on_gas * gas_score +
        gnosis_boost,
    ).to_int(exact=False)
