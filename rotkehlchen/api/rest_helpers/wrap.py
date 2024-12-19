from typing import Final

from rotkehlchen.fval import FVal

TRADES_SCORE: Final = 25
TRANSACTIONS_SCORE: Final = 3
NUM_OF_CHAINS_SCORE: Final = 50
GAS_SCORE: Final = 1500
GNOSIS_BOOST_SCORE: Final = 1000


def calculate_wrap_score(
        num_of_trades: int,
        num_of_transactions: int,
        num_of_chains: int,
        eth_spent_on_gas: FVal,
        gnosis_user: bool,
) -> int:
    """This logic will be deleted once we remove the wrap

    Example score for yabir: 62 * 25 + 3 * 3600 + 7 * 50 + 0.217 * 1500 + 1000 = 14025
    """
    gnosis_boost = GNOSIS_BOOST_SCORE if gnosis_user is True else 0
    return FVal(
        num_of_trades * TRADES_SCORE +
        num_of_transactions * TRANSACTIONS_SCORE +
        num_of_chains * NUM_OF_CHAINS_SCORE +
        eth_spent_on_gas * GAS_SCORE +
        gnosis_boost,
    ).to_int(exact=False)
