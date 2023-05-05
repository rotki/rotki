from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import AcceptableFValInitInput, FVal
from rotkehlchen.types import Price


def deserialize_price(amount: AcceptableFValInitInput) -> Price:
    try:
        result = Price(FVal(amount))
    except ValueError as e:
        raise DeserializationError(f'Failed to deserialize a price/rate entry: {str(e)}') from e

    return result
