from typing import Callable

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.errors import NoPriceForGivenTimestamp
from rotkehlchen.fval import FVal
from rotkehlchen.typing import Timestamp


def assets_exist_at_time(
        base: Asset,
        quote: Asset,
        time: Timestamp,
        price_query: Callable[[Asset, Asset, Timestamp], FVal],
) -> bool:
    """Make sure that the assets exist at the given timestamp"""
    try:
        price = price_query(base, A_USD, time)
        if price == ZERO:
            return False
        price = price_query(quote, A_USD, time)
        if price == ZERO:
            return False
    except NoPriceForGivenTimestamp:
        return False

    return True
