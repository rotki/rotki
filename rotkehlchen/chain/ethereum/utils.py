from rotkehlchen.fval import FVal


def token_normalized_value(token_amount: int, token_decimals: int) -> FVal:
    return token_amount / (FVal(10) ** FVal(token_decimals))
