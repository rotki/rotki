import os
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import UNSUPPORTED_POLONIEX_ASSETS, asset_from_poloniex
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.errors import DeserializationError, UnsupportedAsset
from rotkehlchen.exchanges.data_structures import Loan, Trade, TradeType
from rotkehlchen.exchanges.poloniex import Poloniex, process_polo_loans, trade_from_poloniex
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_DASH
from rotkehlchen.tests.utils.exchanges import POLONIEX_MOCK_DEPOSIT_WITHDRAWALS_RESPONSE
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import Timestamp
from rotkehlchen.user_messages import MessagesAggregator

TEST_RATE_STR = '0.00022999'
TEST_AMOUNT_STR = '613.79427133'
TEST_PERC_FEE_STR = '0.0015'
TEST_POLO_TRADE = {
    'globalTradeID': 192167,
    'tradeID': 3727,
    'date': '2017-07-22 21:18:37',
    'rate': TEST_RATE_STR,
    'amount': TEST_AMOUNT_STR,
    'total': '0.14116654',
    'fee': TEST_PERC_FEE_STR,
    'orderNumber': '2315432',
    'type': 'sell',
    'category': 'exchange',
}
TEST_POLO_LOAN_1 = {
    'id': 3,  # we don't read that in Rotkehlchen
    'rate': '0.001',  # we don't read that in Rotkehlchen
    'duration': '0.001',  # we don't read that in Rotkehlchen
    'interest': '0.00000005',  # we don't read that in Rotkehlchen
    'open': '2017-01-24 06:05:04',
    'close': '2017-01-24 10:05:04',
    'currency': 'DASH',  # cryptocompare hourly DASH/EUR: 13.22106438
    'fee': '0.00015',
    'earned': '0.003',
    'amount': '2',
}
TEST_POLO_LOAN_2 = {
    'id': 4,  # we don't read that in Rotkehlchen
    'rate': '0.001',  # we don't read that in Rotkehlchen
    'duration': '0.001',  # we don't read that in Rotkehlchen
    'interest': '0.00000005',  # we don't read that in Rotkehlchen
    'open': '2017-02-13 19:07:01',
    'close': '2017-02-13 23:05:04',
    'currency': 'DASH',  # cryptocompare hourly DASH/EUR: 15.73995672
    'fee': '0.00011',
    'earned': '0.0035',
    'amount': '2',
}


def test_trade_from_poloniex():
    amount = FVal(TEST_AMOUNT_STR)
    rate = FVal(TEST_RATE_STR)
    perc_fee = FVal(TEST_PERC_FEE_STR)
    cost = amount * rate
    trade = trade_from_poloniex(TEST_POLO_TRADE, 'BTC_ETH')

    assert isinstance(trade, Trade)
    assert isinstance(trade.timestamp, int)
    assert trade.timestamp == 1500758317
    assert trade.trade_type == TradeType.SELL
    assert trade.rate == rate
    assert trade.amount == amount
    assert trade.pair == 'ETH_BTC'
    assert trade.fee == cost * perc_fee
    assert trade.fee_currency == 'BTC'
    assert trade.location == 'poloniex'


def test_poloniex_trade_deserialization_errors():
    test_trade = TEST_POLO_TRADE.copy()
    test_trade['date'] = '2017/07/22 1:18:37'
    with pytest.raises(DeserializationError):
        trade_from_poloniex(test_trade, 'BTC_ETH')

    test_trade = TEST_POLO_TRADE.copy()
    test_trade['type'] = 'lololol'
    with pytest.raises(DeserializationError):
        trade_from_poloniex(test_trade, 'BTC_ETH')

    test_trade = TEST_POLO_TRADE.copy()
    test_trade['amount'] = None
    with pytest.raises(DeserializationError):
        trade_from_poloniex(test_trade, 'BTC_ETH')

    test_trade = TEST_POLO_TRADE.copy()
    test_trade['rate'] = None
    with pytest.raises(DeserializationError):
        trade_from_poloniex(test_trade, 'BTC_ETH')

    test_trade = TEST_POLO_TRADE.copy()
    test_trade['fee'] = ['a']
    with pytest.raises(DeserializationError):
        trade_from_poloniex(test_trade, 'BTC_ETH')

    test_trade = TEST_POLO_TRADE.copy()
    del test_trade['rate']
    with pytest.raises(DeserializationError):
        trade_from_poloniex(test_trade, 'BTC_ETH')


def test_process_polo_loans():
    raw_data = [TEST_POLO_LOAN_1, TEST_POLO_LOAN_2]
    msg_aggregator = MessagesAggregator()
    loans = process_polo_loans(msg_aggregator, raw_data, 0, 1564262858)

    assert len(loans) == 2
    assert isinstance(loans[0], Loan)
    assert loans[0].open_time == Timestamp(1485237904)
    assert loans[0].close_time == Timestamp(1485252304)
    assert isinstance(loans[0].currency, Asset)
    assert loans[0].currency == A_DASH
    assert loans[0].fee == FVal('0.00015')
    assert loans[0].earned == FVal('0.003')
    assert loans[0].amount_lent == FVal('2')

    assert isinstance(loans[1], Loan)
    assert loans[1].open_time == Timestamp(1487012821)
    assert loans[1].close_time == Timestamp(1487027104)
    assert isinstance(loans[1].currency, Asset)
    assert loans[1].currency == A_DASH
    assert loans[1].fee == FVal('0.00011')
    assert loans[1].earned == FVal('0.0035')
    assert loans[1].amount_lent == FVal('2')

    # Test different start/end timestamps
    loans = process_polo_loans(msg_aggregator, raw_data, 1485252305, 1564262858)
    assert len(loans) == 1
    assert loans[0].close_time == Timestamp(1487027104)

    loans = process_polo_loans(msg_aggregator, raw_data, 0, 1487012820)
    assert len(loans) == 1
    assert loans[0].close_time == Timestamp(1485252304)


def test_process_polo_loans_unexpected_data():
    """Test that with unexpected data the offending loan is skipped and an error generated"""
    msg_aggregator = MessagesAggregator()
    broken_loan = TEST_POLO_LOAN_1.copy()
    broken_loan['close'] = 'xx2017-xxs07-22 21:18:37'
    loans = process_polo_loans(msg_aggregator, [broken_loan, TEST_POLO_LOAN_2], 0, 1564262858)
    assert len(loans) == 1
    assert loans[0].close_time == Timestamp(1487027104)
    assert len(msg_aggregator.consume_errors()) == 1

    broken_loan = TEST_POLO_LOAN_1.copy()
    broken_loan['open'] = 'xx2017-xxs07-22 21:18:37'
    loans = process_polo_loans(msg_aggregator, [broken_loan, TEST_POLO_LOAN_2], 0, 1564262858)
    assert len(loans) == 1
    assert loans[0].close_time == Timestamp(1487027104)
    assert len(msg_aggregator.consume_errors()) == 1

    broken_loan = TEST_POLO_LOAN_1.copy()
    broken_loan['fee'] = 'sdad'
    loans = process_polo_loans(msg_aggregator, [broken_loan, TEST_POLO_LOAN_2], 0, 1564262858)
    assert len(loans) == 1
    assert loans[0].close_time == Timestamp(1487027104)
    assert len(msg_aggregator.consume_errors()) == 1

    broken_loan = TEST_POLO_LOAN_1.copy()
    broken_loan['earned'] = None
    loans = process_polo_loans(msg_aggregator, [broken_loan, TEST_POLO_LOAN_2], 0, 1564262858)
    assert len(loans) == 1
    assert loans[0].close_time == Timestamp(1487027104)
    assert len(msg_aggregator.consume_errors()) == 1

    broken_loan = TEST_POLO_LOAN_1.copy()
    broken_loan['amount'] = ['something']
    loans = process_polo_loans(msg_aggregator, [broken_loan, TEST_POLO_LOAN_2], 0, 1564262858)
    assert len(loans) == 1
    assert loans[0].close_time == Timestamp(1487027104)
    assert len(msg_aggregator.consume_errors()) == 1

    # And finally test that missing an expected entry is also handled
    broken_loan = TEST_POLO_LOAN_1.copy()
    del broken_loan['amount']
    loans = process_polo_loans(msg_aggregator, [broken_loan, TEST_POLO_LOAN_2], 0, 1564262858)
    assert len(loans) == 1
    assert loans[0].close_time == Timestamp(1487027104)
    assert len(msg_aggregator.consume_errors()) == 1


def test_poloniex_trade_with_asset_needing_conversion():
    amount = FVal(613.79427133)
    rate = FVal(0.00022999)
    perc_fee = FVal(0.0015)
    poloniex_trade = {
        'globalTradeID': 192167,
        'tradeID': FVal(3727.0),
        'date': '2017-07-22 21:18:37',
        'rate': rate,
        'amount': amount,
        'total': FVal(0.14116654),
        'fee': perc_fee,
        'orderNumber': FVal(2315432.0),
        'type': 'sell',
        'category': 'exchange',
    }
    trade = trade_from_poloniex(poloniex_trade, 'AIR_BTC')
    assert trade.pair == 'BTC_AIR-2'
    assert trade.location == 'poloniex'


def test_query_trade_history_not_shared_cache(data_dir):
    """Test that having 2 different poloniex instances does not use same cache

    Regression test for https://github.com/rotkehlchenio/rotkehlchen/issues/232
    We are using poloniex as an example here. Essentially tests all exchange caches.
    """

    def first_trades(currency_pair, start, end):  # pylint: disable=unused-argument
        return {'BTC': [{'data': 1}]}

    def second_trades(currency_pair, start, end):  # pylint: disable=unused-argument
        return {'BTC': [{'data': 2}]}

    messages_aggregator = MessagesAggregator()
    end_ts = 99999999999
    first_user_dir = os.path.join(data_dir, 'first')
    os.mkdir(first_user_dir)
    second_user_dir = os.path.join(data_dir, 'second')
    os.mkdir(second_user_dir)
    a = Poloniex(b'', b'', first_user_dir, messages_aggregator)
    with patch.object(a, 'return_trade_history', side_effect=first_trades):
        result1 = a.query_trade_history(0, end_ts, end_ts)

    b = Poloniex(b'', b'', second_user_dir, messages_aggregator)
    with patch.object(b, 'return_trade_history', side_effect=second_trades):
        result2 = b.query_trade_history(0, end_ts, end_ts)

    assert result1['BTC'][0]['data'] == 1
    assert result2['BTC'][0]['data'] == 2


def test_poloniex_assets_are_known(poloniex):
    currencies = poloniex.return_currencies()
    for poloniex_asset in currencies.keys():
        try:
            _ = asset_from_poloniex(poloniex_asset)
        except UnsupportedAsset:
            assert poloniex_asset in UNSUPPORTED_POLONIEX_ASSETS


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_poloniex_query_balances_unknown_asset(function_scope_poloniex):
    """Test that if a poloniex balance query returns unknown asset no exception
    is raised and a warning is generated. Same for unsupported assets"""
    poloniex = function_scope_poloniex

    def mock_unknown_asset_return(url, req):  # pylint: disable=unused-argument
        response = MockResponse(
            200,
            """{
            "BTC": {"available": "5.0", "onOrders": "0.5"},
            "ETH": {"available": "10.0", "onOrders": "1.0"},
            "IDONTEXIST": {"available": "1.0", "onOrders": "2.0"},
            "CNOTE": {"available": "2.0", "onOrders": "3.0"}
            }""")
        return response

    with patch.object(poloniex.session, 'post', side_effect=mock_unknown_asset_return):
        # Test that after querying the assets only ETH and BTC are there
        balances, msg = poloniex.query_balances()

    assert msg == ''
    assert len(balances) == 2
    assert balances[A_BTC]['amount'] == FVal('5.5')
    assert balances[A_ETH]['amount'] == FVal('11.0')

    warnings = poloniex.msg_aggregator.consume_warnings()
    assert len(warnings) == 2
    assert 'unknown poloniex asset IDONTEXIST' in warnings[0]
    assert 'unsupported poloniex asset CNOTE' in warnings[1]


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_poloniex_deposits_withdrawal_unknown_asset(function_scope_poloniex):
    """Test that if a poloniex asset movement query returns unknown asset no exception
    is raised and a warning is generated. Same for unsupported assets"""
    poloniex = function_scope_poloniex

    def mock_api_return(url, req):  # pylint: disable=unused-argument
        response = MockResponse(
            200,
            POLONIEX_MOCK_DEPOSIT_WITHDRAWALS_RESPONSE,
        )
        return response

    with patch.object(poloniex.session, 'post', side_effect=mock_api_return):
        # Test that after querying the api only ETH and BTC assets are there
        asset_movements = poloniex.query_deposits_withdrawals(
            start_ts=0,
            end_ts=1488994442,
            end_at_least_ts=1488994442,
        )

    assert len(asset_movements) == 4
    assert asset_movements[0].category == 'withdrawal'
    assert asset_movements[0].timestamp == 1458994442
    assert asset_movements[0].asset == A_BTC
    assert asset_movements[0].amount == FVal('5.0')
    assert asset_movements[0].fee == FVal('0.5')
    assert asset_movements[1].category == 'withdrawal'
    assert asset_movements[1].timestamp == 1468994442
    assert asset_movements[1].asset == A_ETH
    assert asset_movements[1].amount == FVal('10.0')
    assert asset_movements[1].fee == FVal('0.1')

    assert asset_movements[2].category == 'deposit'
    assert asset_movements[2].timestamp == 1448994442
    assert asset_movements[2].asset == A_BTC
    assert asset_movements[2].amount == FVal('50.0')
    assert asset_movements[3].category == 'deposit'
    assert asset_movements[3].timestamp == 1438994442
    assert asset_movements[3].asset == A_ETH
    assert asset_movements[3].amount == FVal('100.0')

    warnings = poloniex.msg_aggregator.consume_warnings()
    assert len(warnings) == 4
    assert 'Found withdrawal of unknown poloniex asset IDONTEXIST' in warnings[0]
    assert 'Found withdrawal of unsupported poloniex asset DIS' in warnings[1]
    assert 'Found deposit of unknown poloniex asset IDONTEXIST' in warnings[2]
    assert 'Found deposit of unsupported poloniex asset EBT' in warnings[3]


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_poloniex_deposits_withdrawal_null_fee(function_scope_poloniex):
    """
    Test that if a poloniex asset movement query returns null for fee we don't crash.
    Regression test for issue #76
    """
    poloniex = function_scope_poloniex

    def mock_api_return(url, req):  # pylint: disable=unused-argument
        response = MockResponse(
            200,
            '{"withdrawals": [{"currency": "FAC", "timestamp": 1478994442, '
            '"amount": "100.5", "fee": null}], "deposits": []}',
        )
        return response

    with patch.object(poloniex.session, 'post', side_effect=mock_api_return):
        asset_movements = poloniex.query_deposits_withdrawals(
            start_ts=0,
            end_ts=1488994442,
            end_at_least_ts=1488994442,
        )

    assert len(asset_movements) == 1
    assert asset_movements[0].category == 'withdrawal'
    assert asset_movements[0].timestamp == 1478994442
    assert asset_movements[0].asset == Asset('FAIR')
    assert asset_movements[0].amount == FVal('100.5')
    assert asset_movements[0].fee == FVal('0')

    warnings = poloniex.msg_aggregator.consume_warnings()
    assert len(warnings) == 0


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_poloniex_deposits_withdrawal_unexpected_data(function_scope_poloniex):
    """
    Test that if a poloniex asset movement query returns unexpected data we handle it gracefully
    """
    poloniex = function_scope_poloniex
    poloniex.cache_ttl_secs = 0

    def mock_poloniex_and_query(given_movements, expected_warnings_num, expected_errors_num):

        def mock_api_return(url, req):  # pylint: disable=unused-argument
            return MockResponse(200, given_movements)

        with patch.object(poloniex.session, 'post', side_effect=mock_api_return):
            asset_movements = poloniex.query_deposits_withdrawals(
                start_ts=0,
                end_ts=1488994442,
                end_at_least_ts=1488994442,
            )

        if expected_errors_num == 0 and expected_warnings_num == 0:
            assert len(asset_movements) == 1
        else:
            assert len(asset_movements) == 0
            warnings = poloniex.msg_aggregator.consume_warnings()
            assert len(warnings) == expected_warnings_num
            errors = poloniex.msg_aggregator.consume_errors()
            assert len(errors) == expected_errors_num

    def check_permutations_of_input_invalid_data(given_input):
        # First make sure it works with normal data
        mock_poloniex_and_query(given_input, expected_warnings_num=0, expected_errors_num=0)

        # From here and on test unexpected data
        # invalid timestamp
        movements = given_input.replace('1478994442', '"dasdsd"')
        mock_poloniex_and_query(movements, expected_warnings_num=0, expected_errors_num=1)

        # invalid amount
        movements = given_input.replace('"100.5"', 'null')
        mock_poloniex_and_query(movements, expected_warnings_num=0, expected_errors_num=1)

        # invalid fee
        if 'fee' in given_input:
            movements = given_input.replace('"0.1"', '"dasdsdsad"')
            mock_poloniex_and_query(movements, expected_warnings_num=0, expected_errors_num=1)

        # invalid currency type
        movements = given_input.replace('"FAC"', '[]')
        mock_poloniex_and_query(movements, expected_warnings_num=0, expected_errors_num=1)

        # unknown currency
        movements = given_input.replace('"FAC"', '"DSDSDSD"')
        mock_poloniex_and_query(movements, expected_warnings_num=1, expected_errors_num=0)

        # missing key error
        movements = given_input.replace('"timestamp": 1478994442,', '')
        mock_poloniex_and_query(movements, expected_warnings_num=0, expected_errors_num=1)

    input_withdrawals = """
    {"withdrawals": [{"currency": "FAC", "timestamp": 1478994442,
    "amount": "100.5", "fee": "0.1"}], "deposits": []}"""
    check_permutations_of_input_invalid_data(input_withdrawals)
    input_deposits = """
    {"deposits": [{"currency": "FAC", "timestamp": 1478994442,
    "amount": "100.5"}], "withdrawals": []}"""
    check_permutations_of_input_invalid_data(input_deposits)
