import os
import warnings as test_warnings
from collections import defaultdict
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_BCH, A_BTC, A_ETH, A_GUSD, A_LINK, A_LTC, A_USD
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.asset import UnknownAsset, UnprocessableTradePair, UnsupportedAsset
from rotkehlchen.exchanges.gemini import gemini_symbol_to_base_quote
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.fixtures.exchanges.gemini import (
    SANDBOX_GEMINI_WP_API_KEY,
    SANDBOX_GEMINI_WP_API_SECRET,
)
from rotkehlchen.tests.utils.constants import A_PAXG, A_ZEC
from rotkehlchen.tests.utils.exchanges import get_exchange_asset_symbols
from rotkehlchen.tests.utils.globaldb import is_asset_symbol_unsupported
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Location, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_now

UNSUPPORTED_GEMINI_PAIRS = {'btcgusdperp', 'ethgusdperp', 'pepegusdperp'}


@pytest.mark.skipif('CI' in os.environ, reason='temporarily skip gemini in CI')
def test_gemini_validate_key(sandbox_gemini):
    """Test that validate api key works for a correct api key

    Uses the Gemini sandbox
    """
    result, msg = sandbox_gemini.validate_api_key()
    assert result is True
    assert msg == ''


@pytest.mark.skipif('CI' in os.environ, reason='temporarily skip gemini in CI')
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


@pytest.mark.skipif('CI' in os.environ, reason='temporarily skip gemini in CI')
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


@pytest.mark.skipif('CI' in os.environ, reason='temporarily skip gemini in CI')
@pytest.mark.parametrize('gemini_test_base_uri', ['https://api.gemini.com'])
def test_gemini_all_symbols_are_known(sandbox_gemini, globaldb):
    """Test that the gemini trade pairs are all supported by rotki

    Use the real gemini API
    """
    for asset in get_exchange_asset_symbols(Location.GEMINI):
        assert is_asset_symbol_unsupported(globaldb, Location.GEMINI, asset) is False, f'Gemini assets {asset} should not be unsupported'  # noqa: E501

    symbols = sandbox_gemini._public_api_query('symbols')
    for symbol in symbols:
        try:
            base, quote = gemini_symbol_to_base_quote(symbol)
            assert base is not None
            assert quote is not None

        except UnprocessableTradePair as e:
            if symbol not in UNSUPPORTED_GEMINI_PAIRS:
                test_warnings.warn(UserWarning(
                    f'UnprocessableTradePair in Gemini. {e}',
                ))
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Unknown Gemini asset detected. {e} Symbol: {symbol}',
            ))
        except UnsupportedAsset as e:
            assert globaldb.is_asset_symbol_unsupported(globaldb, Location.GEMINI, str(e).split(' ')[2])  # noqa: PT017, E501


@pytest.mark.skipif('CI' in os.environ, reason='temporarily skip gemini in CI')
@pytest.mark.parametrize('gemini_sandbox_api_key', [SANDBOX_GEMINI_WP_API_KEY])
@pytest.mark.parametrize('gemini_sandbox_api_secret', [SANDBOX_GEMINI_WP_API_SECRET])
def test_gemini_wrong_key_permissions(sandbox_gemini):
    """Test that using a gemini key that does not have the auditor permission is detected"""
    result, _ = sandbox_gemini.validate_api_key()
    assert not result


@pytest.mark.skipif('CI' in os.environ, reason='temporarily skip gemini in CI')
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


@pytest.mark.skipif('CI' in os.environ, reason='temporarily skip gemini in CI')
def test_gemini_query_trades(sandbox_gemini):
    """Test that querying the trades endpoint works correctly

    Uses the Gemini sandbox
    """
    with patch.object(sandbox_gemini, '_query_asset_movements'):
        events, _ = sandbox_gemini.query_online_history_events(
            start_ts=Timestamp(0),
            end_ts=Timestamp(1584881354),
        )

    assert events == [SwapEvent(
        timestamp=TimestampMS(1584720549000),
        location=Location.GEMINI,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USD,
        amount=FVal('3311.315'),
        location_label='gemini',
        unique_id='560627330',
    ), SwapEvent(
        timestamp=TimestampMS(1584720549000),
        location=Location.GEMINI,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BTC,
        amount=FVal('0.5'),
        location_label='gemini',
        unique_id='560627330',
    ), SwapEvent(
        timestamp=TimestampMS(1584720549000),
        location=Location.GEMINI,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USD,
        amount=FVal('33.11315'),
        location_label='gemini',
        unique_id='560627330',
    ), SwapEvent(
        timestamp=TimestampMS(1584721109000),
        location=Location.GEMINI,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal('1'),
        location_label='gemini',
        unique_id='560628883',
    ), SwapEvent(
        timestamp=TimestampMS(1584721109000),
        location=Location.GEMINI,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USD,
        amount=FVal('20.00'),
        location_label='gemini',
        unique_id='560628883',
    ), SwapEvent(
        timestamp=TimestampMS(1584721109000),
        location=Location.GEMINI,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USD,
        amount=FVal('0.20'),
        location_label='gemini',
        unique_id='560628883',
    )]


@pytest.mark.skipif('CI' in os.environ, reason='temporarily skip gemini in CI')
def test_gemini_query_all_trades_pagination(sandbox_gemini):
    """Test that querying the trades endpoint works correctly including
    combining results from multiple requests

    Uses the Gemini sandbox at which we've made quite a few test trades
    """
    with patch.object(sandbox_gemini, '_query_asset_movements'):
        events, _ = sandbox_gemini.query_online_history_events(
            start_ts=Timestamp(0),
            end_ts=ts_now(),
        )

    identifiers = defaultdict(int)
    for event in events:
        # The same event_identifier can be present up to 3 times (spend/receive/fee events).
        assert identifiers[event.event_identifier] <= 3, 'trade included multiple times in the results'  # noqa: E501
        identifiers[event.event_identifier] += 1

    assert len(events) == 1773


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


@pytest.mark.skipif('CI' in os.environ, reason='temporarily skip gemini in CI')
def test_gemini_query_deposits_withdrawals(sandbox_gemini):
    """Test that querying the asset movements endpoint works correctly

    Since Gemini sandbox does not support transfers, this uses a mocked call.
    """
    transfers_patch = mock_gemini_transfers(sandbox_gemini, requests.post)

    with transfers_patch, patch.object(sandbox_gemini, '_query_trades'):
        sandbox_gemini.query_history_events()

    with sandbox_gemini.db.conn.read_ctx() as cursor:
        movements = DBHistoryEvents(sandbox_gemini.db).get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(location=Location.GEMINI),
            has_premium=True,
        )

    assert len(movements) == 6
    expected_movements = [AssetMovement(
        identifier=1,
        location=Location.GEMINI,
        location_label=sandbox_gemini.name,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1535451930000),
        asset=A_USD,
        amount=FVal('1.00'),
        unique_id='341167014',
        extra_data={
            'address': '0xd24400ae8BfEBb18cA49Be86258a3C749cf46853',
            'transaction_id': '7bffd85893ee8e72e31061a84d25c45f2c4537c2f765a1e79feb06a7294445c3',
        },
    ), AssetMovement(
        identifier=6,
        location=Location.GEMINI,
        location_label=sandbox_gemini.name,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1507913541000),
        asset=A_USD,
        amount=FVal('36.00'),
        unique_id='320013281',
    ), AssetMovement(
        identifier=5,
        location=Location.GEMINI,
        location_label=sandbox_gemini.name,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1499990797000),
        asset=A_ETH,
        amount=FVal('100'),
        unique_id='309356152',
        extra_data={'transaction_id': '605c5fa8bf99458d24d61e09941bc443ddc44839d9aaa508b14b296c0c8269b2'},  # noqa: E501
    ), AssetMovement(
        identifier=4,
        location=Location.GEMINI,
        location_label=sandbox_gemini.name,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1495550176000),
        asset=A_BTC,
        amount=FVal('1500'),
        unique_id='298112782',
        extra_data={'transaction_id': '163eeee4741f8962b748289832dd7f27f754d892f5d23bf3ea6fba6e350d9ce3'},  # noqa: E501
    ), AssetMovement(
        identifier=3,
        location=Location.GEMINI,
        location_label=sandbox_gemini.name,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1458862076000),
        asset=A_USD,
        amount=FVal('500.00'),
        unique_id='265799530',
    ), AssetMovement(
        identifier=2,
        location=Location.GEMINI,
        location_label=sandbox_gemini.name,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1450403787000),
        asset=A_BTC,
        amount=FVal('5'),
        unique_id='82897811',
        extra_data={
            'address': 'mqjvCtt4TJfQaC7nUgLMvHwuDPXMTEUGqx',
            'transaction_id': 'c458b86955b80db0718cfcadbff3df3734a906367982c6eb191e61117b810bbb',
        },
    )]
    # The deposits should be returned with the oldest first (so given list is reversed)
    assert movements == expected_movements[::-1]


def test_gemini_symbol_to_base_quote():
    """Test quote asset detection and validation for gemini symbols"""
    assert gemini_symbol_to_base_quote('btcusd') == (A_BTC, A_USD)
    assert gemini_symbol_to_base_quote('linkbtc') == (A_LINK, A_BTC)
    assert gemini_symbol_to_base_quote('btcgusd') == (A_BTC, A_GUSD)
    assert gemini_symbol_to_base_quote('linkpaxg') == (A_LINK, A_PAXG)
    assert gemini_symbol_to_base_quote('moodengusd') == (Asset('MOODENG'), A_USD)

    with pytest.raises(UnprocessableTradePair):
        gemini_symbol_to_base_quote('btcusdperp')
    with pytest.raises(UnknownAsset):
        gemini_symbol_to_base_quote('zzzusd')
    with pytest.raises(UnknownAsset):
        gemini_symbol_to_base_quote('linkzzz')
