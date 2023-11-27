import warnings as test_warnings
from unittest.mock import patch

import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.converters import asset_from_coinbase
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_1INCH, A_BTC, A_ETH, A_USD, A_USDC
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.exchanges.coinbase import Coinbase, trade_from_conversion
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.exchanges import (
    BUYS_RESPONSE,
    DEPOSITS_RESPONSE,
    SELLS_RESPONSE,
    WITHDRAWALS_RESPONSE,
    mock_normal_coinbase_query,
)
from rotkehlchen.tests.utils.history import TEST_END_TS
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import AssetMovementCategory, Location, TimestampMS, TradeType


def test_name():
    exchange = Coinbase('coinbase1', 'a', b'a', object(), object())
    assert exchange.location == Location.COINBASE
    assert exchange.name == 'coinbase1'


def test_coinbase_query_balances(function_scope_coinbase):
    """Test that coinbase balance query works fine for the happy path"""
    coinbase = function_scope_coinbase

    def mock_coinbase_accounts(url, timeout):  # pylint: disable=unused-argument
        response = MockResponse(
            200,
            """
{
  "pagination": {
    "ending_before": null,
    "starting_after": null,
    "limit": 25,
    "order": "desc",
    "previous_uri": null,
    "next_uri": null
  },
  "data": [
    {
      "id": "58542935-67b5-56e1-a3f9-42686e07fa40",
      "name": "My Vault",
      "primary": false,
      "type": "vault",
      "currency": "BTC",
      "balance": {
        "amount": "4.00000000",
        "currency": "BTC"
      },
      "created_at": "2015-01-31T20:49:02Z",
      "updated_at": "2015-01-31T20:49:02Z",
      "resource": "account",
      "resource_path": "/v2/accounts/58542935-67b5-56e1-a3f9-42686e07fa40",
      "ready": true
    },
    {
      "id": "2bbf394c-193b-5b2a-9155-3b4732659ede",
      "name": "My Wallet",
      "primary": true,
      "type": "wallet",
      "currency": "ETH",
      "balance": {
        "amount": "39.59000000",
        "currency": "ETH"
      },
      "created_at": "2015-01-31T20:49:02Z",
      "updated_at": "2015-01-31T20:49:02Z",
      "resource": "account",
      "resource_path": "/v2/accounts/2bbf394c-193b-5b2a-9155-3b4732659ede"
    },
    {
      "id": "68542935-67b5-56e1-a3f9-42686e07fa40",
      "name": "Another Wallet",
      "primary": false,
      "type": "vault",
      "currency": "BTC",
      "balance": {
        "amount": "1.230000000",
        "currency": "BTC"
      },
      "created_at": "2015-01-31T20:49:02Z",
      "updated_at": "2015-01-31T20:49:02Z",
      "resource": "account",
      "resource_path": "/v2/accounts/68542935-67b5-56e1-a3f9-42686e07fa40",
      "ready": true
    }
  ]
}
            """,
        )
        return response

    with patch.object(coinbase.session, 'get', side_effect=mock_coinbase_accounts):
        balances, msg = coinbase.query_balances()

    assert msg == ''
    assert len(balances) == 2
    assert balances[A_BTC].amount == FVal('5.23')
    assert balances[A_BTC].usd_value == FVal('7.8450000000')
    assert balances[A_ETH].amount == FVal('39.59')
    assert balances[A_ETH].usd_value == FVal('59.385000000')

    warnings = coinbase.msg_aggregator.consume_warnings()
    errors = coinbase.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0


def test_coinbase_query_balances_unexpected_data(function_scope_coinbase):
    """Test that coinbase balance query works fine for the happy path"""
    coinbase = function_scope_coinbase
    coinbase.cache_ttl_secs = 0
    data = """{
    "data": [
    {
      "id": "58542935-67b5-56e1-a3f9-42686e07fa40",
      "name": "My Vault",
      "primary": false,
      "type": "vault",
      "currency": "BTC",
      "balance": {
        "amount": "4.00000000",
        "currency": "BTC"
      },
      "created_at": "2015-01-31T20:49:02Z",
      "updated_at": "2015-01-31T20:49:02Z",
      "resource": "account",
      "resource_path": "/v2/accounts/58542935-67b5-56e1-a3f9-42686e07fa40",
      "ready": true
    }]}"""

    def query_coinbase_and_test_local_mock(
            response_str,
            expected_warnings_num,
            expected_errors_num,
            contains_expected_msg=None,
    ):
        def mock_coinbase_accounts(url, timeout):  # pylint: disable=unused-argument
            return MockResponse(200, response_str)

        with patch.object(coinbase.session, 'get', side_effect=mock_coinbase_accounts):
            balances, msg = coinbase.query_balances()

        warnings = coinbase.msg_aggregator.consume_warnings()
        errors = coinbase.msg_aggregator.consume_errors()
        if contains_expected_msg:
            assert balances is None
            assert contains_expected_msg in msg
        elif expected_errors_num == 0 and expected_warnings_num == 0:
            assert len(warnings) == 0
            assert len(errors) == 0
            assert msg == ''
            assert len(balances) == 1
            assert balances[A_BTC].amount == FVal('4')
            assert balances[A_BTC].usd_value == FVal('6')
        else:
            assert len(warnings) == expected_warnings_num
            assert len(errors) == expected_errors_num
            assert msg == ''
            assert len(balances) == 0

    # test that all is fine with normal data
    query_coinbase_and_test_local_mock(data, expected_warnings_num=0, expected_errors_num=0)

    # From now on unexpected data
    # no data key
    query_coinbase_and_test_local_mock(
        '{"foo": 1}',
        expected_warnings_num=0,
        expected_errors_num=0,
        contains_expected_msg='Coinbase API request failed. Check logs for more details',
    )
    # account entry without "balance" key
    input_data = data.replace('"balance"', '"foo"')
    query_coinbase_and_test_local_mock(input_data, expected_warnings_num=0, expected_errors_num=1)
    # account entry without amount in "balance"
    input_data = data.replace('"amount"', '"foo"')
    query_coinbase_and_test_local_mock(input_data, expected_warnings_num=0, expected_errors_num=1)
    # account entry without currency in "balance"
    input_data = data.replace('"currency"', '"foo"')
    query_coinbase_and_test_local_mock(input_data, expected_warnings_num=0, expected_errors_num=1)
    # account entry with invalid balance amount
    input_data = data.replace('"4.00000000"', '"csadasdsd"')
    query_coinbase_and_test_local_mock(input_data, expected_warnings_num=0, expected_errors_num=1)
    # account entry with unknown asset
    input_data = data.replace('"BTC"', '"DDSADSAD"')
    query_coinbase_and_test_local_mock(input_data, expected_warnings_num=1, expected_errors_num=0)
    # account entry with invalid asset
    input_data = data.replace('"BTC"', 'null')
    query_coinbase_and_test_local_mock(input_data, expected_warnings_num=0, expected_errors_num=1)


def test_coinbase_query_trade_history(function_scope_coinbase):
    """Test that coinbase trade history query works fine for the happy path"""
    coinbase = function_scope_coinbase

    with patch.object(coinbase.session, 'get', side_effect=mock_normal_coinbase_query):
        trades = coinbase.query_trade_history(
            start_ts=0,
            end_ts=TEST_END_TS,
            only_cache=False,
        )

    warnings = coinbase.msg_aggregator.consume_warnings()
    errors = coinbase.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0
    assert len(trades) == 2
    expected_trades = [Trade(
        timestamp=1459024920,
        location=Location.COINBASE,
        base_asset=A_ETH,
        quote_asset=A_USD,
        trade_type=TradeType.SELL,
        amount=FVal('100.45'),
        rate=FVal('88.90014932802389248382279741'),
        fee=FVal('10.1'),
        fee_currency=A_USD,
        link='1e14d574-30fa-5d85-b02c-6be0d851d61d',
    ), Trade(
        timestamp=1500705839,
        location=Location.COINBASE,
        base_asset=A_BTC,
        quote_asset=A_USD,
        trade_type=TradeType.BUY,
        amount=FVal('486.34313725'),
        rate=FVal('9.997920454875299055122012005'),
        fee=FVal('1.01'),
        fee_currency=A_USD,
        link='9e14d574-30fa-5d85-b02c-6be0d851d61d',
    )]
    assert trades == expected_trades

    # and now try only a smaller time range
    with patch.object(coinbase.session, 'get', side_effect=mock_normal_coinbase_query):
        trades = coinbase.query_trade_history(
            start_ts=0,
            end_ts=1459024921,
            only_cache=False,
        )

    warnings = coinbase.msg_aggregator.consume_warnings()
    errors = coinbase.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0
    assert len(trades) == 1
    assert trades[0].trade_type == TradeType.SELL
    assert trades[0].timestamp == 1459024920


def query_coinbase_and_test(
        coinbase,
        query_fn_name,
        buys_response=BUYS_RESPONSE,
        buys_paginated_end=BUYS_RESPONSE,
        sells_response=SELLS_RESPONSE,
        sells_paginated_end=SELLS_RESPONSE,
        deposits_response=DEPOSITS_RESPONSE,
        withdrawals_response=WITHDRAWALS_RESPONSE,
        expected_warnings_num=0,
        expected_errors_num=0,
        # Since this test only mocks as breaking only one of the two actions by default
        expected_actions_num=1,
):
    def mock_coinbase_query(url, **kwargs):  # pylint: disable=unused-argument
        if 'buys' in url:
            if 'next-page' in url:
                return MockResponse(200, buys_paginated_end)
            # else
            return MockResponse(200, buys_response)
        if 'sells' in url:
            if 'next-page' in url:
                return MockResponse(200, sells_paginated_end)
            # else
            return MockResponse(200, sells_response)
        if 'deposits' in url:
            return MockResponse(200, deposits_response)
        if 'withdrawals' in url:
            return MockResponse(200, withdrawals_response)
        if 'accounts' in url:
            # keep it simple just return a single ID and ignore the rest of the fields
            return MockResponse(200, '{"data": [{"id": "5fs23"}]}')
        # else
        raise AssertionError(f'Unexpected url {url} for test')

    query_fn = getattr(coinbase, query_fn_name)
    with patch.object(coinbase.session, 'get', side_effect=mock_coinbase_query):
        if query_fn_name == 'query_online_trade_history':
            actions, _ = query_fn(
                start_ts=0,
                end_ts=TEST_END_TS,
            )
        else:
            actions = query_fn(
                start_ts=0,
                end_ts=TEST_END_TS,
            )

    errors = coinbase.msg_aggregator.consume_errors()
    warnings = coinbase.msg_aggregator.consume_warnings()
    if expected_errors_num == 0 and expected_warnings_num == 0 and expected_actions_num == 1:
        assert len(actions) == 2
        assert len(errors) == 0
        assert len(warnings) == 0
    else:
        assert len(actions) == expected_actions_num
        assert len(errors) == expected_errors_num
        assert len(warnings) == expected_warnings_num


def test_coinbase_query_trade_history_unexpected_data(function_scope_coinbase):
    """Test that coinbase trade history query handles unexpected data properly"""
    coinbase = function_scope_coinbase
    coinbase.cache_ttl_secs = 0

    # first query with proper data and expect no errors
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        expected_warnings_num=0,
        expected_errors_num=0,
    )

    # fallback to payout_at if created_date is missing
    broken_response = BUYS_RESPONSE.replace('"created_at": "2017-07-21T23:43:59-07:00",', '')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=0,
    )

    # invalid created_at timestamp
    broken_response = SELLS_RESPONSE.replace('"2016-03-26T13:42:00-07:00"', '"dadssd"')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        sells_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # unknown asset
    broken_response = BUYS_RESPONSE.replace('"BTC"', '"dsadsad"')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        buys_response=broken_response,
        expected_warnings_num=1,
        expected_errors_num=0,
    )

    # invalid asset format
    broken_response = BUYS_RESPONSE.replace('"BTC"', '123')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid trade type
    broken_response = BUYS_RESPONSE.replace('"buy"', 'null')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid amount
    broken_response = BUYS_RESPONSE.replace('"486.34313725"', '"gfgfg"')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid subtotal amount
    broken_response = BUYS_RESPONSE.replace('"4862.42"', 'false')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid fee amount
    broken_response = BUYS_RESPONSE.replace('"1.01"', '"aas"')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # unknown fee asset
    broken_response = BUYS_RESPONSE.replace('"USD"', '"DSADSA"')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        buys_response=broken_response,
        expected_warnings_num=1,
        expected_errors_num=0,
    )

    # invalid fee asset
    broken_response = BUYS_RESPONSE.replace('"USD"', '[]')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # missing key error
    broken_response = SELLS_RESPONSE.replace('  "status": "completed",', '')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )


def test_coinbase_query_trade_history_paginated(function_scope_coinbase):
    """Test that coinbase trade history query can deal with paginated response"""
    coinbase = function_scope_coinbase
    coinbase.cache_ttl_secs = 0

    paginated_buys_response = BUYS_RESPONSE.replace(
        '"next_uri": null',
        '"next_uri": "/v2/buys/?next-page"',
    )

    paginated_sells_response = SELLS_RESPONSE.replace(
        '"next_uri": null',
        '"next_uri": "/v2/sells/?next-page"',
    )

    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        expected_warnings_num=0,
        expected_errors_num=0,
        expected_actions_num=4,
        buys_response=paginated_buys_response,
        sells_response=paginated_sells_response,
    )


def test_coinbase_query_deposit_withdrawals(function_scope_coinbase):
    """Test that coinbase deposit/withdrawals history query works fine for the happy path"""
    coinbase = function_scope_coinbase

    with patch.object(coinbase.session, 'get', side_effect=mock_normal_coinbase_query):
        movements = coinbase.query_online_deposits_withdrawals(
            start_ts=0,
            end_ts=1566726126,
        )

    warnings = coinbase.msg_aggregator.consume_warnings()
    errors = coinbase.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0
    assert len(movements) == 5
    expected_movements = [AssetMovement(
        location=Location.COINBASE,
        category=AssetMovementCategory.DEPOSIT,
        timestamp=1519001640,
        address=None,
        transaction_id=None,
        asset=A_USD,
        amount=FVal('55.00'),
        fee_asset=A_USD,
        fee=FVal('0.05'),
        link='1130eaec-07d7-54c4-a72c-2e92826897df',
    ), AssetMovement(
        location=Location.COINBASE,
        category=AssetMovementCategory.WITHDRAWAL,
        address=None,
        transaction_id=None,
        timestamp=1485895742,
        asset=A_USD,
        amount=FVal('10.00'),
        fee_asset=A_USD,
        fee=FVal('0.01'),
        link='146eaec-07d7-54c4-a72c-2e92826897df',
    ), AssetMovement(
        location=Location.COINBASE,
        category=AssetMovementCategory.WITHDRAWAL,
        address='0x6dcD6449dbCa615e40d696328209686eA95327b2',
        transaction_id='0x558bfa4d2a4ef598ddb92233459c00eda9e6c14cda75e6773b90208cb6938169',
        timestamp=1566726126,
        asset=A_ETH,
        amount=FVal('0.05770427'),
        fee_asset=A_ETH,
        fee=FVal('0.00021'),
        link='https://etherscan.io/tx/bbb',
    ), AssetMovement(
        location=Location.COINBASE,
        category=AssetMovementCategory.WITHDRAWAL,
        address='0x6dcD6449dbCa615e40d696328209686eA95327b2',
        transaction_id=None,
        timestamp=1566726126,
        asset=A_ETH,
        amount=FVal('0.05770427'),
        fee_asset=A_ETH,
        fee=ZERO,
        link='id2',
    ), AssetMovement(
        location=Location.COINBASE,
        category=AssetMovementCategory.DEPOSIT,
        address=None,
        transaction_id='ccc',
        timestamp=1502554304,
        asset=A_BTC,
        amount=FVal('0.10181673'),
        fee_asset=A_BTC,
        fee=ZERO,
        link='https://blockchain.info/tx/ccc',
    )]
    assert expected_movements == movements

    # and now try to query within a specific range
    with patch.object(coinbase.session, 'get', side_effect=mock_normal_coinbase_query):
        movements = coinbase.query_online_deposits_withdrawals(
            start_ts=0,
            end_ts=1519001640,
        )

    warnings = coinbase.msg_aggregator.consume_warnings()
    errors = coinbase.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0
    assert len(movements) == 3
    assert movements[0].category == AssetMovementCategory.DEPOSIT
    assert movements[0].timestamp == 1519001640
    assert movements[1].category == AssetMovementCategory.WITHDRAWAL
    assert movements[1].timestamp == 1485895742
    assert movements[2].category == AssetMovementCategory.DEPOSIT
    assert movements[2].timestamp == 1502554304


def test_coinbase_query_income_loss_expense(
        function_scope_coinbase,
        price_historian,    # pylint: disable=unused-argument
):
    """Test that coinbase deposit/withdrawals history query works fine for the happy path"""
    coinbase = function_scope_coinbase

    with patch.object(coinbase.session, 'get', side_effect=mock_normal_coinbase_query):
        events = coinbase.query_online_income_loss_expense(
            start_ts=0,
            end_ts=1611426233,
        )

    warnings = coinbase.msg_aggregator.consume_warnings()
    errors = coinbase.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0
    assert len(events) == 2
    expected_events = [
        HistoryEvent(
            event_identifier='CBE_id4',
            sequence_index=0,
            timestamp=TimestampMS(1609877514000),
            location=Location.COINBASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=asset_from_coinbase('NMR'),
            balance=Balance(amount=FVal('0.02762431'), usd_value=FVal('1.01')),
            notes='Received 0.02762431 NMR ($1.01)',
        ), HistoryEvent(
            event_identifier='CBE_id5',
            sequence_index=0,
            timestamp=TimestampMS(1611426233000),
            location=Location.COINBASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=asset_from_coinbase('ALGO'),
            balance=Balance(amount=FVal('0.000076'), usd_value=ZERO),
            notes='Received 0.000076 ALGO ($0.00)',
        ),
    ]
    assert expected_events == events

    # and now try to query within a specific range
    with patch.object(coinbase.session, 'get', side_effect=mock_normal_coinbase_query):
        events = coinbase.query_online_income_loss_expense(
            start_ts=0,
            end_ts=1609877514,
        )

    warnings = coinbase.msg_aggregator.consume_warnings()
    errors = coinbase.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0
    assert events == [expected_events[0]]


def test_coinbase_query_deposit_withdrawals_unexpected_data(function_scope_coinbase):
    """Test that coinbase deposit/withdrawals query handles unexpected data properly"""
    coinbase = function_scope_coinbase

    # first query with proper data and expect no errors
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_deposits_withdrawals',
        expected_warnings_num=0,
        expected_errors_num=0,
    )

    # invalid payout_at timestamp
    broken_response = DEPOSITS_RESPONSE.replace('"2018-02-18T16:54:00-08:00"', '"dadas"')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_deposits_withdrawals',
        deposits_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid created_at timestamp
    broken_response = WITHDRAWALS_RESPONSE.replace('"2017-01-31T20:49:02Z"', '"dadssd"')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_deposits_withdrawals',
        withdrawals_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid asset movement type
    broken_response = WITHDRAWALS_RESPONSE.replace('"withdrawal"', 'null')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_deposits_withdrawals',
        withdrawals_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # unknown asset
    broken_response = WITHDRAWALS_RESPONSE.replace('"USD"', '"dasdad"')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_deposits_withdrawals',
        withdrawals_response=broken_response,
        expected_warnings_num=1,
        expected_errors_num=0,
    )

    # invalid asset
    broken_response = WITHDRAWALS_RESPONSE.replace('"USD"', '{}')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_deposits_withdrawals',
        withdrawals_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid amount
    broken_response = WITHDRAWALS_RESPONSE.replace('"10.00"', 'true')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_deposits_withdrawals',
        withdrawals_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid fee
    broken_response = WITHDRAWALS_RESPONSE.replace('"0.01"', '"dasd"')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_deposits_withdrawals',
        withdrawals_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # missing key error
    broken_response = DEPOSITS_RESPONSE.replace('      "resource": "deposit",', '')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_deposits_withdrawals',
        deposits_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )


def test_asset_conversion():
    trade_b = {
        'id': '77c5ad72-764e-414b-8bdb-b5aed20fb4b1',
        'type': 'trade',
        'status': 'completed',
        'amount': {
            'amount': '-1000.000000',
            'currency': 'USDC',
        },
        'native_amount': {
            'amount': '-1000.00',
            'currency': 'USD',
        },
        'description': None,
        'created_at': '2020-06-08T02:32:15Z',
        'updated_at': '2021-06-08T02:32:16Z',
        'resource': 'transaction',
        'resource_path': '/v2/accounts/sd5af/transactions/77c5ad72-764e-414b-8bdb-b5aed20fb4b1',
        'instant_exchange': False,
        'trade': {
            'id': '5dceef97-ef34-41e6-9171-3e60cd01639e',
            'resource': 'trade',
            'resource_path': '/v2/accounts/sd5af/trades/5dceef97-ef34-41e6-9171-3e60cd01639e',
        },
        'details': {
            'title': 'Converted from USD Coin',
            'subtitle': 'Using USDC Wallet',
            'header': 'Converted 1,000.0000 USDC ($1,000.00)',
            'health': 'positive',
            'payment_method_name': 'USDC Wallet',
        },
    }

    trade_a = {
        'id': '8f530cd1-5ec0-4aae-afdc-198502a53b17',
        'type': 'trade',
        'status': 'completed',
        'amount': {
            'amount': '0.01694165',
            'currency': 'BTC',
        },
        'native_amount': {
            'amount': '910.00',
            'currency': 'USD',
        },
        'description': None,
        'created_at': '2020-06-08T02:32:16Z',
        'updated_at': '2020-06-08T02:32:16Z',
        'resource': 'transaction',
        'resource_path': '/v2/accounts/sd5af/transactions/8f530cd1-5ec0-4aae-afdc-198502a53b17',
        'instant_exchange': False,
        'trade': {
            'id': '5dceef97-ef34-41e6-9171-3e60cd01639e',
            'resource': 'trade',
            'resource_path': '/v2/accounts/sd5af/trades/5dceef97-ef34-41e6-9171-3e60cd01639e',
        },
        'details': {
            'title': 'Converted to Bitcoin',
            'subtitle': 'Using USDC Wallet',
            'header': 'Converted 0.01694165 BTC ($910.00)',
            'health': 'positive',
            'payment_method_name': 'USDC Wallet',
        },
    }

    trade = trade_from_conversion(trade_a, trade_b)
    expected_trade = Trade(
        timestamp=1623119536,
        location=Location.COINBASE,
        base_asset=A_USDC,
        quote_asset=A_BTC,
        trade_type=TradeType.SELL,
        amount=FVal('1000.0'),
        rate=FVal('0.00001694165'),
        fee=FVal('90'),
        fee_currency=A_USDC,
        link='5dceef97-ef34-41e6-9171-3e60cd01639e',
    )
    assert trade == expected_trade


def test_asset_conversion_not_stable_coin():
    """Test a conversion using a from asset that is not a stable coin"""
    trade_a = {
        'id': '77c5ad72-764e-414b-8bdb-b5aed20fb4b1',
        'type': 'trade',
        'status': 'completed',
        'amount': {
            'amount': '-6000.000000',
            'currency': '1INCH',
        },
        'native_amount': {
            'amount': '-1000.00',
            'currency': 'USD',
        },
        'description': None,
        'created_at': '2020-06-08T02:32:15Z',
        'updated_at': '2021-06-08T02:32:16Z',
        'resource': 'transaction',
        'resource_path': '/v2/accounts/sd5af/transactions/77c5ad72-764e-414b-8bdb-b5aed20fb4b1',
        'instant_exchange': False,
        'trade': {
            'id': '5dceef97-ef34-41e6-9171-3e60cd01639e',
            'resource': 'trade',
            'resource_path': '/v2/accounts/sd5af/trades/5dceef97-ef34-41e6-9171-3e60cd01639e',
        },
        'details': {
            'title': 'Converted from USD Coin',
            'subtitle': 'Using USDC Wallet',
            'header': 'Converted 1,000.0000 USDC ($1,000.00)',
            'health': 'positive',
            'payment_method_name': 'USDC Wallet',
        },
    }

    trade_b = {
        'id': '8f530cd1-5ec0-4aae-afdc-198502a53b17',
        'type': 'trade',
        'status': 'completed',
        'amount': {
            'amount': '0.01694165',
            'currency': 'BTC',
        },
        'native_amount': {
            'amount': '910.00',
            'currency': 'USD',
        },
        'description': None,
        'created_at': '2020-06-08T02:32:16Z',
        'updated_at': '2020-06-08T02:32:16Z',
        'resource': 'transaction',
        'resource_path': '/v2/accounts/sd5af/transactions/8f530cd1-5ec0-4aae-afdc-198502a53b17',
        'instant_exchange': False,
        'trade': {
            'id': '5dceef97-ef34-41e6-9171-3e60cd01639e',
            'resource': 'trade',
            'resource_path': '/v2/accounts/sd5af/trades/5dceef97-ef34-41e6-9171-3e60cd01639e',
        },
        'details': {
            'title': 'Converted to Bitcoin',
            'subtitle': 'Using USDC Wallet',
            'header': 'Converted 0.01694165 BTC ($910.00)',
            'health': 'positive',
            'payment_method_name': 'USDC Wallet',
        },
    }

    trade = trade_from_conversion(trade_a, trade_b)
    expected_trade = Trade(
        timestamp=1623119536,
        location=Location.COINBASE,
        base_asset=A_1INCH,
        quote_asset=A_BTC,
        trade_type=TradeType.SELL,
        amount=FVal('6000.0'),
        rate=FVal('0.000002823608333333333333333333333'),
        fee=FVal('540'),
        fee_currency=A_1INCH,
        link='5dceef97-ef34-41e6-9171-3e60cd01639e',
    )
    assert trade == expected_trade


def test_asset_conversion_zero_fee():
    """Test a conversion with 0 fee"""
    trade_a = {
        'id': '77c5ad72-764e-414b-8bdb-b5aed20fb4b1',
        'type': 'trade',
        'status': 'completed',
        'amount': {
            'amount': '-6000.000000',
            'currency': '1INCH',
        },
        'native_amount': {
            'amount': '-1000.00',
            'currency': 'USD',
        },
        'description': None,
        'created_at': '2020-06-08T02:32:16Z',
        'updated_at': '2021-06-08T02:32:16Z',
        'resource': 'transaction',
        'resource_path': '/v2/accounts/sd5af/transactions/77c5ad72-764e-414b-8bdb-b5aed20fb4b1',
        'instant_exchange': False,
        'trade': {
            'id': '5dceef97-ef34-41e6-9171-3e60cd01639e',
            'resource': 'trade',
            'resource_path': '/v2/accounts/sd5af/trades/5dceef97-ef34-41e6-9171-3e60cd01639e',
        },
        'details': {
            'title': 'Converted from USD Coin',
            'subtitle': 'Using USDC Wallet',
            'header': 'Converted 1,000.0000 USDC ($1,000.00)',
            'health': 'positive',
            'payment_method_name': 'USDC Wallet',
        },
    }

    trade_b = {
        'id': '8f530cd1-5ec0-4aae-afdc-198502a53b17',
        'type': 'trade',
        'status': 'completed',
        'amount': {
            'amount': '0.01694165',
            'currency': 'BTC',
        },
        'native_amount': {
            'amount': '1000.00',
            'currency': 'USD',
        },
        'description': None,
        'created_at': '2020-06-08T02:32:16Z',
        'updated_at': '2020-06-08T02:32:16Z',
        'resource': 'transaction',
        'resource_path': '/v2/accounts/sd5af/transactions/8f530cd1-5ec0-4aae-afdc-198502a53b17',
        'instant_exchange': False,
        'trade': {
            'id': '5dceef97-ef34-41e6-9171-3e60cd01639e',
            'resource': 'trade',
            'resource_path': '/v2/accounts/sd5af/trades/5dceef97-ef34-41e6-9171-3e60cd01639e',
        },
        'details': {
            'title': 'Converted to Bitcoin',
            'subtitle': 'Using USDC Wallet',
            'header': 'Converted 0.01694165 BTC ($910.00)',
            'health': 'positive',
            'payment_method_name': 'USDC Wallet',
        },
    }

    trade = trade_from_conversion(trade_a, trade_b)
    expected_trade = Trade(
        timestamp=1623119536,
        location=Location.COINBASE,
        base_asset=A_1INCH,
        quote_asset=A_BTC,
        trade_type=TradeType.SELL,
        amount=FVal('6000.0'),
        rate=FVal('0.000002823608333333333333333333333'),
        fee=FVal(ZERO),
        fee_currency=A_1INCH,
        link='5dceef97-ef34-41e6-9171-3e60cd01639e',
    )
    assert trade == expected_trade


def test_asset_conversion_choosing_fee_asset():
    """Test that the fee asset is correctly chosen when the received asset transaction
    is created before the giving transaction.
    """

    trade_a = {
        'id': 'REDACTED',
        'type': 'trade',
        'status': 'completed',
        'amount': {
            'amount': '-37734.034561',
            'currency': 'ETH',
        },
        'native_amount': {
            'amount': '-79362.22',
            'currency': 'USD',
        },
        'description': None,
        'created_at': '2021-10-12T13:23:56Z',
        'updated_at': '2021-10-12T13:23:56Z',
        'resource': 'transaction',
        'resource_path': '/v2/accounts/REDACTED/transactions/REDACTED',
        'instant_exchange': False,
        'trade': {
            'id': 'id_of_trade',
            'resource': 'trade',
            'resource_path': '/v2/accounts/REDACTED/trades/id_of_trade',
        },
        'details': {
            'title': 'Converted from ETH',
            'subtitle': 'Using ETH Wallet',
            'header': 'Converted 37,734.034561 ETH ($79,362.22)',
            'health': 'positive',
            'payment_method_name': 'ETH Wallet',
        },
        'hide_native_amount': False,
    }

    trade_b = {
        'id': 'REDACTED',
        'type': 'trade',
        'status': 'completed',
        'amount': {
            'amount': '552.315885836',
            'currency': 'BTC',
        },
        'native_amount': {
            'amount': '77827.94',
            'currency': 'USD',
        },
        'description': None,
        'created_at': '2021-10-12T13:23:55Z',
        'updated_at': '2021-10-12T13:23:57Z',
        'resource': 'transaction',
        'resource_path': '/v2/accounts/REDACTED/transactions/REDACTED',
        'instant_exchange': False,
        'trade': {
            'id': 'id_of_trade',
            'resource': 'trade',
            'resource_path': '/v2/accounts/REDACTED/trades/id_of_trade',
        },
        'details': {
            'title': 'Converted to BTC',
            'subtitle': 'Using ETH Wallet',
            'header': 'Converted 552.31588584 BTC ($77,827.94)',
            'health': 'positive',
            'payment_method_name': 'ETH Wallet',
        },
        'hide_native_amount': False,
    }

    trade = trade_from_conversion(trade_a, trade_b)
    expected_trade = Trade(
        timestamp=1634045036,
        location=Location.COINBASE,
        base_asset=A_ETH,
        quote_asset=A_BTC,
        trade_type=TradeType.SELL,
        amount=FVal('37734.034561'),
        rate=FVal('0.01463707478571204566189616471'),
        fee=FVal('10.88821337581925051594581586'),
        fee_currency=A_BTC,
        link='id_of_trade',
    )
    assert trade == expected_trade


def test_coverage_of_products():
    """Test that we can process all assets from coinbase"""
    data = requests.get('https://api.exchange.coinbase.com/currencies')
    for coin in data.json():
        try:
            # Make sure all products can be processed
            asset_from_coinbase(coin['id'])
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Found unknown asset {e.identifier} with symbol {coin["id"]} in Coinbase. '
                f'Support for it has to be added',
            ))
