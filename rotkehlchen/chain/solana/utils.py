from rotkehlchen.fval import FVal


def lamports_to_sol(amount: int) -> FVal:
    """One SOL is 1e9 lamports. Similar concept as wei in the Ethereum ecosystem"""
    return FVal(amount / 1_000_000_000)
