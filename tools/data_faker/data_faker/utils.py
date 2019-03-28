from typing import Callable

from rotkehlchen.assets import Asset
from rotkehlchen.constants import S_USD, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history import NoPriceForGivenTimestamp
from rotkehlchen.typing import Timestamp


def assets_exist_at_time(
        base: Asset,
        quote: Asset,
        time: Timestamp,
        price_query: Callable[[Asset, Asset, Timestamp], FVal],
) -> bool:
    """Make sure that the assets exist at the given timestamp"""
    try:
        price = price_query(base, S_USD, time)
        if price == ZERO:
            return False
        price = price_query(quote, S_USD, time)
        if price == ZERO:
            return False
    except NoPriceForGivenTimestamp:
        return False

    return True
