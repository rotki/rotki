import warnings as test_warnings
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.constants.assets import A_BCH, A_BTC, A_ETH, A_LINK, A_LTC, A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import UnknownAsset, UnprocessableTradePair
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade, TradeType
from rotkehlchen.exchanges.gemini import gemini_symbol_to_base_quote
from rotkehlchen.fval import FVal
from rotkehlchen.tests.fixtures.exchanges.gemini import (
    SANDBOX_GEMINI_WP_API_KEY,
    SANDBOX_GEMINI_WP_API_SECRET,
)
from rotkehlchen.tests.utils.constants import A_PAXG, A_ZEC
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import AssetMovementCategory, Location, Timestamp
from rotkehlchen.utils.misc import ts_now


def test_gemini_validate_key(sandbox_gemini):
    """Test that validate api key works for a correct api key

    Uses the Gemini sandbox
    """
    result, msg = sandbox_gemini.validate_api_key()
    assert result is True
    assert msg == ''


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
    """Test that the gemini trade pairs are all supported by rotki

    Use the real gemini API
    """
    symbols = sandbox_gemini._public_api_query('symbols')
    for symbol in symbols:
        try:
            base, quote = gemini_symbol_to_base_quote(symbol)
        except UnprocessableTradePair as e:
            test_warnings.warn(UserWarning(
                f'UnprocessableTradePair in Gemini. {e}',
            ))
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Unknown Gemini asset detected. {e}',
            ))

        assert base is not None
        assert quote is not None


@pytest.mark.parametrize('gemini_sandbox_api_key', [SANDBOX_GEMINI_WP_API_KEY])
@pytest.mark.parametrize('gemini_sandbox_api_secret', [SANDBOX_GEMINI_WP_API_SECRET])
def test_gemini_wrong_key_permissions(sandbox_gemini):
    """Test that using a gemini key that does not have the auditor permission is detected"""
    result, _ = sandbox_gemini.validate_api_key()
    assert not result


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_gemini_query_balances(sandbox_gemini):
    """Test that querying the balances endpoint works correctly

    Uses the Gemini sandbox
    """
    balances, msg = sandbox_gemini.query_balances()
    assert msg == ''
    assert len(balances) == 6

    assert balances[A_USD].amount == FVal('723384.71365986583339')
    assert balances[A_USD].usd_value == balances[A_USD].amount
    assert balances[A_ETH].amount == FVal('59985.07921584')
    assert balances[A_ETH].usd_value > ZERO
    assert balances[A_LTC].amount == FVal('60000')
    assert balances[A_LTC].usd_value > ZERO
    assert balances[A_BTC].amount == FVal('2888.7177526197')
    assert balances[A_BTC].usd_value > ZERO
    assert balances[A_ZEC].amount == FVal('60000')
    assert balances[A_ZEC].usd_value > ZERO
    assert balances[A_BCH].amount == FVal('60000')
    assert balances[A_BCH].usd_value > ZERO


def test_gemini_query_trades(sandbox_gemini):
    """Test that querying the trades endpoint works correctly

    Uses the Gemini sandbox
    """
    trades = sandbox_gemini.query_trade_history(
        start_ts=0,
        end_ts=Timestamp(1584881354),
        only_cache=False,
    )
    assert len(trades) == 2
    assert trades[0] == Trade(
        timestamp=Timestamp(1584720549),
        location=Location.GEMINI,
        base_asset=A_BTC,
        quote_asset=A_USD,
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
        base_asset=A_ETH,
        quote_asset=A_USD,
        trade_type=TradeType.SELL,
        amount=FVal('1.0'),
        rate=FVal('20.0'),
        fee=FVal('0.2'),
        fee_currency=A_USD,
        link='560628883',
        notes='',
    )


def test_gemini_query_all_trades_pagination(sandbox_gemini):
    """Test that querying the trades endpoint works correctly including
    combining results from multiple requests

    Uses the Gemini sandbox at which we've made quite a few test trades
    """
    trades = sandbox_gemini.query_trade_history(start_ts=0, end_ts=ts_now(), only_cache=False)
    identifiers = set()
    for trade in trades:
        assert trade.link not in identifiers, 'trade included multiple times in the results'
        identifiers.add(trade.link)
    assert len(trades) == 591


# Taken from the API docs
TRANSFERS_RESPONSE = """[
   {
      "type":"Deposit",
      "status":"Advanced",
      "timestampms":1507913541275,
      "eid":320013281,
      "currency":"USD",
      "amount":"36.00",
      "method":"ACH"
   },
   {
      "type":"Deposit",
      "status":"Advanced",
      "timestampms":1499990797452,
      "eid":309356152,
      "currency":"ETH",
      "amount":"100",
      "txHash":"605c5fa8bf99458d24d61e09941bc443ddc44839d9aaa508b14b296c0c8269b2"
   },
   {
      "type":"Deposit",
      "status":"Complete",
      "timestampms":1495550176562,
      "eid":298112782,
      "currency":"BTC",
      "amount":"1500",
      "txHash":"163eeee4741f8962b748289832dd7f27f754d892f5d23bf3ea6fba6e350d9ce3",
      "outputIdx":0
   },
   {
      "type":"Deposit",
      "status":"Advanced",
      "timestampms":1458862076082,
      "eid":265799530,
      "currency":"USD",
      "amount":"500.00",
      "method":"ACH"
   },
   {
      "type":"Withdrawal",
      "status":"Complete",
      "timestampms":1450403787001,
      "eid":82897811,
      "currency":"BTC",
      "amount":"5",
      "txHash":"c458b86955b80db0718cfcadbff3df3734a906367982c6eb191e61117b810bbb",
      "outputIdx":0,
      "destination":"mqjvCtt4TJfQaC7nUgLMvHwuDPXMTEUGqx"
   },
   {
      "type": "Withdrawal",
      "status": "Complete",
      "timestampms": 1535451930431,
      "eid": 341167014,
      "currency": "USD",
      "amount": "1.00",
      "txHash": "7bffd85893ee8e72e31061a84d25c45f2c4537c2f765a1e79feb06a7294445c3",
      "destination": "0xd24400ae8BfEBb18cA49Be86258a3C749cf46853"
   }
]"""


def mock_gemini_transfers(gemini, original_requests_request):
    def mock_requests_requests(method, url, *args, **kwargs):
        if 'transfers' not in url:
            return original_requests_request(method, url, *args, **kwargs)

        return MockResponse(200, TRANSFERS_RESPONSE)

    return patch.object(gemini.session, 'request', wraps=mock_requests_requests)


def test_gemini_query_deposits_withdrawals(sandbox_gemini):
    """Test that querying the asset movements endpoint works correctly

    Since Gemini sandbox does not support transfers, this uses a mocked call.
    """
    transfers_patch = mock_gemini_transfers(sandbox_gemini, requests.post)

    with transfers_patch:
        movements = sandbox_gemini.query_deposits_withdrawals(
            start_ts=0,
            end_ts=Timestamp(1584881354),
            only_cache=False,
        )

    assert len(movements) == 6
    expected_movements = [AssetMovement(
        location=Location.GEMINI,
        category=AssetMovementCategory.DEPOSIT,
        timestamp=Timestamp(1507913541),
        address=None,
        transaction_id=None,
        asset=A_USD,
        amount=FVal('36'),
        fee_asset=A_USD,
        fee=ZERO,
        link='320013281',
    ), AssetMovement(
        location=Location.GEMINI,
        category=AssetMovementCategory.DEPOSIT,
        address=None,
        transaction_id='605c5fa8bf99458d24d61e09941bc443ddc44839d9aaa508b14b296c0c8269b2',
        timestamp=Timestamp(1499990797),
        asset=A_ETH,
        amount=FVal('100'),
        fee_asset=A_ETH,
        fee=ZERO,
        link='309356152',
    ), AssetMovement(
        location=Location.GEMINI,
        category=AssetMovementCategory.DEPOSIT,
        address=None,
        transaction_id='163eeee4741f8962b748289832dd7f27f754d892f5d23bf3ea6fba6e350d9ce3',
        timestamp=Timestamp(1495550176),
        asset=A_BTC,
        amount=FVal('1500'),
        fee_asset=A_BTC,
        fee=ZERO,
        link='298112782',
    ), AssetMovement(
        location=Location.GEMINI,
        category=AssetMovementCategory.DEPOSIT,
        address=None,
        transaction_id=None,
        timestamp=Timestamp(1458862076),
        asset=A_USD,
        amount=FVal('500'),
        fee_asset=A_USD,
        fee=ZERO,
        link='265799530',
    ), AssetMovement(
        location=Location.GEMINI,
        category=AssetMovementCategory.WITHDRAWAL,
        address='mqjvCtt4TJfQaC7nUgLMvHwuDPXMTEUGqx',
        transaction_id='c458b86955b80db0718cfcadbff3df3734a906367982c6eb191e61117b810bbb',
        timestamp=Timestamp(1450403787),
        asset=A_BTC,
        amount=FVal('5'),
        fee_asset=A_BTC,
        fee=ZERO,
        link='82897811',
    ), AssetMovement(
        location=Location.GEMINI,
        category=AssetMovementCategory.WITHDRAWAL,
        address='0xd24400ae8BfEBb18cA49Be86258a3C749cf46853',
        transaction_id='7bffd85893ee8e72e31061a84d25c45f2c4537c2f765a1e79feb06a7294445c3',
        timestamp=Timestamp(1535451930),
        asset=A_USD,
        amount=FVal('1'),
        fee_asset=A_USD,
        fee=ZERO,
        link='341167014',
    )]
    # The deposits should be returned with the oldest first (so given list is reversed)
    assert movements == expected_movements[::-1]


def test_gemini_symbol_to_base_quote():
    """Test edge cases and not yet existing cases of gemini symbol to pair"""
    assert gemini_symbol_to_base_quote('btclink') == (A_BTC, A_LINK)
    assert gemini_symbol_to_base_quote('linkbtc') == (A_LINK, A_BTC)
    assert gemini_symbol_to_base_quote('linkpaxg') == (A_LINK, A_PAXG)
    assert gemini_symbol_to_base_quote('paxglink') == (A_PAXG, A_LINK)

    with pytest.raises(UnprocessableTradePair):
        gemini_symbol_to_base_quote('btclinkxyz')
    with pytest.raises(UnprocessableTradePair):
        gemini_symbol_to_base_quote('xyzbtclink')
    with pytest.raises(UnknownAsset):
        gemini_symbol_to_base_quote('zzzbtc')
    with pytest.raises(UnknownAsset):
        gemini_symbol_to_base_quote('linkzzz')
    with pytest.raises(UnknownAsset):
        gemini_symbol_to_base_quote('zzzlink')
    with pytest.raises(UnknownAsset):
        gemini_symbol_to_base_quote('zzzzlink')
    with pytest.raises(UnknownAsset):
        gemini_symbol_to_base_quote('linkzzzz')
