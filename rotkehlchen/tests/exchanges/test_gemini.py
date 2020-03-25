import pytest

from rotkehlchen.constants.assets import A_BCH, A_BTC, A_ETH, A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade, TradeType
from rotkehlchen.exchanges.gemini import gemini_symbol_to_pair
from rotkehlchen.fval import FVal
from rotkehlchen.tests.fixtures.exchanges.gemini import (
    SANDBOX_GEMINI_WP_API_KEY,
    SANDBOX_GEMINI_WP_API_SECRET,
)
from rotkehlchen.tests.utils.constants import A_LTC, A_ZEC
from rotkehlchen.typing import ApiKey, ApiSecret, Fee, Location, Timestamp, TradePair
from rotkehlchen.utils.misc import ts_now


@pytest.mark.parametrize('gemini_sandbox_api_secret', [b'16NFMLWrVWf1TrHQtVExRFmBovnq'])
def test_gemini_wrong_secret(sandbox_gemini):
    """Test that giving wrong api secret is detected

    Uses the Gemini sandbox
    """
    result, _ = sandbox_gemini.validate_api_key()
    assert not result
    balances, msg = sandbox_gemini.query_balances()
    assert balances is None
    assert 'Invalid API Key or API secret' in msg


@pytest.mark.parametrize('gemini_sandbox_api_key', ['fddad'])
def test_gemini_wrong_key(sandbox_gemini):
    """Test that giving wrong api key is detected

    Uses the Gemini sandbox
    """
    result, _ = sandbox_gemini.validate_api_key()
    assert not result
    balances, msg = sandbox_gemini.query_balances()
    assert balances is None
    assert 'Invalid API Key or API secret' in msg


@pytest.mark.parametrize('gemini_test_base_uri', ['https://api.gemini.com'])
def test_gemini_all_symbols_are_known(sandbox_gemini):
    """Test that the gemini trade pairs are all supported by Rotki

    Use the real gemini API
    """
    symbols = sandbox_gemini._public_api_query('symbols')
    for symbol in symbols:
        pair = gemini_symbol_to_pair(symbol)
        assert pair is not None


@pytest.mark.parametrize('gemini_sandbox_api_key', [SANDBOX_GEMINI_WP_API_KEY])
@pytest.mark.parametrize('gemini_sandbox_api_secret', [SANDBOX_GEMINI_WP_API_SECRET])
def test_gemini_wrong_key_permissions(sandbox_gemini):
    """Test that using a gemini key that does not have the auditor permission is detected"""
    result, _ = sandbox_gemini.validate_api_key()
    assert not result


def test_gemini_query_balances(sandbox_gemini):
    """Test that querying the balances endpoint works correctly

    Uses the Gemini sandbox
    """
    balances, msg = sandbox_gemini.query_balances()
    assert msg == ''
    assert len(balances) == 6
    assert balances[A_USD]['amount'] == FVal('96675.37185')
    assert balances[A_USD]['usd_value'] == balances[A_USD]['amount']
    assert balances[A_ETH]['amount'] == FVal('19999')
    assert balances[A_ETH]['usd_value'] > ZERO
    assert balances[A_LTC]['amount'] == FVal('20000')
    assert balances[A_LTC]['usd_value'] > ZERO
    assert balances[A_BTC]['amount'] == FVal('1000.5')
    assert balances[A_BTC]['usd_value'] > ZERO
    assert balances[A_ZEC]['amount'] == FVal('20000')
    assert balances[A_ZEC]['usd_value'] > ZERO
    assert balances[A_BCH]['amount'] == FVal('20000')
    assert balances[A_BCH]['usd_value'] > ZERO


def test_gemini_query_trades(sandbox_gemini):
    """Test that querying the trades endpoint works correctly

    Uses the Gemini sandbox
    """
    trades = sandbox_gemini.query_trade_history(start_ts=0, end_ts=Timestamp(1584881354))
    assert len(trades) == 2
    assert trades[0] == Trade(
        timestamp=Timestamp(1584720549),
        location=Location.GEMINI,
        pair='BTC_USD',
        trade_type=TradeType.BUY,
        amount=FVal('0.5'),
        rate=FVal('6622.63'),
        fee=FVal('33.11315'),
        fee_currency=A_USD,
        link='560627330',
        notes='',
    )
    assert trades[1] == Trade(
        timestamp=Timestamp(1584721109),
        location=Location.GEMINI,
        pair='ETH_USD',
        trade_type=TradeType.SELL,
        amount=FVal('1.0'),
        rate=FVal('20.0'),
        fee=FVal('0.2'),
        fee_currency=A_USD,
        link='560628883',
        notes='',
    )
