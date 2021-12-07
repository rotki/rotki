import pytest

from rotkehlchen.constants.assets import A_3CRV, A_BSQ
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import RemoteError
from rotkehlchen.externalapis.bisq_market import get_bisq_market_price
from rotkehlchen.typing import Price


def test_market_request():
    """Test that we can query bisq for market prices"""
    price = get_bisq_market_price(A_BSQ)
    assert price != Price(ZERO)
    # Test that error is correctly raised when there is no market
    with pytest.raises(RemoteError):
        get_bisq_market_price(A_3CRV)
