from rotkehlchen.constants.assets import A_BCH, A_BTC, A_ETH, A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_LTC, A_ZEC


def test_gemini_query_balances(sandbox_gemini):
    """Test that querying the balances endpoint works correctly

    Uses the Gemini sandbox
    """
    balances = sandbox_gemini.query_balances()
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
