import os

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_BCH, A_BTC, A_ETH, A_EUR, A_USD, A_USDC, A_USDT
from rotkehlchen.exchanges.krakenfutures import Krakenfutures
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_GBP, A_LTC, A_XRP
from rotkehlchen.types import Location


@pytest.mark.skipif('CI' in os.environ, reason='temporarily skip kraken in CI')
def test_kraken_validate_key(demo_kraken_futures):
    """Test that validate api key works for a correct api key

    Uses the kraken demo
    """
    result, msg = demo_kraken_futures.validate_api_key()
    assert result is True
    assert msg == ''


def test_querying_balances(demo_kraken_futures):
    balances, error_or_empty = demo_kraken_futures.query_balances()
    assert error_or_empty == ''
    assert isinstance(balances, dict)
    for asset, entry in balances.items():
        assert isinstance(asset, Asset)
        assert isinstance(entry, Balance)

    assert balances[A_USD].amount == FVal('10076.53008268181')
    assert balances[A_USD].usd_value > ZERO
    assert balances[A_EUR].amount == FVal('10000')
    assert balances[A_EUR].usd_value > ZERO
    assert balances[A_GBP].amount == FVal('3791.9006')
    assert balances[A_GBP].usd_value > ZERO
    assert balances[A_ETH].amount == FVal('4.7153945058')
    assert balances[A_ETH].usd_value > ZERO
    assert balances[A_LTC].amount == FVal('104.3821723602')
    assert balances[A_LTC].usd_value > ZERO
    assert balances[A_BTC].amount == FVal('0.1574971479')
    assert balances[A_BTC].usd_value > ZERO
    assert balances[A_BCH].amount == FVal('20.0369882804')
    assert balances[A_BCH].usd_value > ZERO
    assert balances[A_XRP].amount == FVal('4427.7371164')
    assert balances[A_XRP].usd_value > ZERO
    assert balances[A_USDC.identifier].amount == FVal('5000.65008452')
    assert balances[A_USDC.identifier].usd_value > ZERO
    assert balances[A_USDT.identifier].amount == FVal('5003.96313881')
    assert balances[A_USDT.identifier].usd_value > ZERO


@pytest.mark.skipif('CI' in os.environ, reason='temporarily skip kraken in CI')
@pytest.mark.parametrize('kraken_demo_api_secret', [b'16NFMLWrVWf1TrHQtVExRFmBovnq'])
def test_kraken_wrong_secret(demo_kraken_futures):
    """Test that giving wrong api secret is detected

    Uses the kraken demo
    """
    result, _ = demo_kraken_futures.validate_api_key()
    assert not result
    balances, msg = demo_kraken_futures.query_balances()
    assert balances is None
    assert 'authenticationError' in msg


@pytest.mark.skipif('CI' in os.environ, reason='temporarily skip kraken in CI')
@pytest.mark.parametrize('kraken_demo_api_key', ['fddad'])
def test_kraken_wrong_key(demo_kraken_futures):
    """Test that giving wrong api key is detected

    Uses the kraken demo
    """
    result, _ = demo_kraken_futures.validate_api_key()
    assert not result
    balances, msg = demo_kraken_futures.query_balances()
    assert balances is None
    assert 'authenticationError' in msg


def test_name():
    exchange = Krakenfutures(
        'Kraken Futures 1', 'a', b'YQ==', object(), object(),  # b'YQ==' is base64 for 'a'
    )
    assert exchange.location == Location.KRAKENFUTURES
    assert exchange.name == 'Kraken Futures 1'
