from unittest.mock import patch

import pytest

from rotkehlchen.constants.assets import A_3CRV, A_BSQ
from rotkehlchen.constants.misc import ZERO_PRICE
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.bisq_market import get_bisq_market_price


def test_market_request():
    """Test that we can query bisq for market prices"""
    price_in_btc = get_bisq_market_price(A_BSQ.resolve_to_crypto_asset())
    assert price_in_btc != ZERO_PRICE
    # Test that error is correctly raised when there is no market
    with patch('rotkehlchen.externalapis.bisq_market.DEFAULT_TIMEOUT_TUPLE', new=(1, 1)), pytest.raises(RemoteError):  # noqa: E501
        get_bisq_market_price(A_3CRV.resolve_to_crypto_asset())
