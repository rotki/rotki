import pytest

from rotkehlchen.constants.assets import A_BCH, A_BTC, A_ETH, A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_LTC, A_ZEC


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
