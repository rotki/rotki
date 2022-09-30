import warnings as test_warnings
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import UNSUPPORTED_POLONIEX_ASSETS, asset_from_poloniex
from rotkehlchen.assets.exchanges_mappings.poloniex import WORLD_TO_POLONIEX
from rotkehlchen.constants.assets import A_BCH, A_BTC, A_ETH
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import Trade, TradeType
from rotkehlchen.exchanges.poloniex import Poloniex, trade_from_poloniex
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_AIR2
from rotkehlchen.tests.utils.exchanges import (
    POLONIEX_BALANCES_RESPONSE,
    POLONIEX_MOCK_DEPOSIT_WITHDRAWALS_RESPONSE,
    POLONIEX_TRADES_RESPONSE,
)
from rotkehlchen.tests.utils.history import assert_poloniex_asset_movements
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import AssetMovementCategory, Location

TEST_RATE_STR = '0.00022999'
TEST_AMOUNT_STR = '613.79427133'
TEST_FEE_STR = '0.920691406995'
TEST_POLO_TRADE = {
    'symbol': 'ETH_BTC',
    'id': 192167,
    'createTime': 1500758317000,
    'price': TEST_RATE_STR,
    'quantity': TEST_AMOUNT_STR,
    'feeCurrency': 'BTC',
    'feeAmount': TEST_FEE_STR,
    'side': 'SELL',
    'type': 'MARKET',
    'accountType': 'SPOT',
}


def test_name():
    exchange = Poloniex('poloniex1', 'a', b'a', object(), object())
    assert exchange.location == Location.POLONIEX
    assert exchange.name == 'poloniex1'


def test_trade_from_poloniex():
    amount = FVal(TEST_AMOUNT_STR)
    rate = FVal(TEST_RATE_STR)
    fee = FVal(TEST_FEE_STR)
    trade = trade_from_poloniex(TEST_POLO_TRADE)

    assert isinstance(trade, Trade)
    assert isinstance(trade.timestamp, int)
    assert trade.timestamp == 1500758317
    assert trade.trade_type == TradeType.SELL
    assert trade.rate == rate
    assert trade.amount == amount
    assert trade.base_asset == A_ETH
    assert trade.quote_asset == A_BTC
    assert trade.fee == fee
    assert trade.fee_currency == A_BTC
    assert trade.location == Location.POLONIEX


def test_poloniex_trade_deserialization_errors():
    test_trade = TEST_POLO_TRADE.copy()
    test_trade['createTime'] = 'dsadsad'
    with pytest.raises(DeserializationError):
        trade_from_poloniex(test_trade)

    test_trade = TEST_POLO_TRADE.copy()
    test_trade['side'] = 'lololol'
    with pytest.raises(DeserializationError):
        trade_from_poloniex(test_trade)

    test_trade = TEST_POLO_TRADE.copy()
    test_trade['quantity'] = None
    with pytest.raises(DeserializationError):
        trade_from_poloniex(test_trade)

    test_trade = TEST_POLO_TRADE.copy()
    test_trade['price'] = None
    with pytest.raises(DeserializationError):
        trade_from_poloniex(test_trade)

    test_trade = TEST_POLO_TRADE.copy()
    test_trade['feeAmount'] = ['a']
    with pytest.raises(DeserializationError):
        trade_from_poloniex(test_trade)

    test_trade = TEST_POLO_TRADE.copy()
    del test_trade['price']
    with pytest.raises(DeserializationError):
        trade_from_poloniex(test_trade)


def test_poloniex_trade_with_asset_needing_conversion():
    amount = FVal(613.79427133)
    rate = FVal(0.00022999)
    fee = FVal(0.001)
    poloniex_trade = {
        'id': 15,
        'symbol': 'BTC_AIR',
        'createTime': 1500758317000,
        'price': rate,
        'quantity': amount,
        'feeAmount': fee,
        'feeCurrency': 'AIR',
        'type': 'LIMIT',
        'side': 'SELL',
    }
    trade = trade_from_poloniex(poloniex_trade)
    assert trade.base_asset == A_BTC
    assert trade.quote_asset == A_AIR2
    assert trade.fee_currency == A_AIR2
    assert trade.location == Location.POLONIEX


def test_query_trade_history(function_scope_poloniex):
    """Happy path test for poloniex trade history querying"""
    poloniex = function_scope_poloniex

    def mock_api_return(url, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, POLONIEX_TRADES_RESPONSE)

    with patch.object(poloniex.session, 'get', side_effect=mock_api_return):
        trades = poloniex.query_trade_history(
            start_ts=0,
            end_ts=1565732120,
            only_cache=False,
        )

    assert len(trades) == 2
    assert trades[0].timestamp == 1539709423
    assert trades[0].location == Location.POLONIEX
    assert trades[0].base_asset == A_ETH
    assert trades[0].quote_asset == A_BTC
    assert trades[0].trade_type == TradeType.BUY
    assert trades[0].amount == FVal('3600.53748129')
    assert trades[0].rate == FVal('0.00003432')
    assert trades[0].fee.is_close(FVal('7.20107496258'))
    assert isinstance(trades[0].fee_currency, Asset)
    assert trades[0].fee_currency == A_ETH

    assert trades[1].timestamp == 1539713117
    assert trades[1].location == Location.POLONIEX
    assert trades[1].base_asset == A_BCH
    assert trades[1].quote_asset == A_BTC
    assert trades[1].trade_type == TradeType.SELL
    assert trades[1].amount == FVal('1.40308443')
    assert trades[1].rate == FVal('0.06935244')
    assert trades[1].fee.is_close(FVal('0.00009730732'))
    assert isinstance(trades[1].fee_currency, Asset)
    assert trades[1].fee_currency == A_BTC


def test_query_trade_history_unexpected_data(function_scope_poloniex):
    """Test that poloniex trade history querying returning unexpected data is handled gracefully"""
    poloniex = function_scope_poloniex
    poloniex.cache_ttl_secs = 0

    def mock_poloniex_and_query(given_trades, expected_warnings_num, expected_errors_num, expected_trades_len=0):  # noqa: E501

        def mock_api_return(url, **kwargs):  # pylint: disable=unused-argument
            return MockResponse(200, given_trades)

        with patch.object(poloniex.session, 'get', side_effect=mock_api_return):
            trades, _ = poloniex.query_online_trade_history(
                start_ts=0,
                end_ts=1565732120,
            )

        assert len(trades) == expected_trades_len
        warnings = poloniex.msg_aggregator.consume_warnings()
        assert len(warnings) == expected_warnings_num
        errors = poloniex.msg_aggregator.consume_errors()
        assert len(errors) == expected_errors_num

    input_trades = """[{
    "symbol": "ETH_BTC",
    "id": 13536350,
    "createTime": 1539709423000,
    "price": "0.00003432",
    "quantity": "3600.53748129",
    "feeAmount": "7.20107496258",
    "feeCurrency": "ETH",
    "side": "BUY",
    "type": "MARKET",
    "accountType": "SPOT"}]"""

    # First make sure it works with normal data
    mock_poloniex_and_query(input_trades, expected_warnings_num=0, expected_errors_num=0, expected_trades_len=1)  # noqa: E501

    # from here and on invalid data
    # invalid timestamp
    given_input = input_trades.replace('1539709423000', '"435345"')
    mock_poloniex_and_query(given_input, expected_warnings_num=0, expected_errors_num=1)

    # invalid symbol
    given_input = input_trades.replace('"ETH_BTC"', '"0"')
    mock_poloniex_and_query(given_input, expected_warnings_num=0, expected_errors_num=1)

    # symbol with unknown asset
    given_input = input_trades.replace('"ETH_BTC"', '"ETH_SDSDSD"')
    mock_poloniex_and_query(given_input, expected_warnings_num=1, expected_errors_num=0)

    # symbol with unsupported asset
    given_input = input_trades.replace('"ETH_BTC"', '"ETH_BALLS"')
    mock_poloniex_and_query(given_input, expected_warnings_num=1, expected_errors_num=0)

    # invalid price
    given_input = input_trades.replace('"0.00003432"', 'null')
    mock_poloniex_and_query(given_input, expected_warnings_num=0, expected_errors_num=1)

    # invalid amount
    given_input = input_trades.replace('"3600.53748129"', '"dsadsd"')
    mock_poloniex_and_query(given_input, expected_warnings_num=0, expected_errors_num=1)

    # invalid fee
    given_input = input_trades.replace('"7.20107496258"', '"dasdsad"')
    mock_poloniex_and_query(given_input, expected_warnings_num=0, expected_errors_num=1)

    # invalid trade side
    given_input = input_trades.replace('"BUY"', '"dasdsdad"')
    mock_poloniex_and_query(given_input, expected_warnings_num=0, expected_errors_num=1)

    # invalid accountType
    given_input = input_trades.replace('"SPOT"', '"dsadsdsadd"')
    mock_poloniex_and_query(given_input, expected_warnings_num=0, expected_errors_num=0)


def test_poloniex_assets_are_known(poloniex):
    unsupported_assets = set(UNSUPPORTED_POLONIEX_ASSETS)
    common_items = unsupported_assets.intersection(set(WORLD_TO_POLONIEX.values()))
    assert not common_items, f'Poloniex assets {common_items} should not be unsupported'
    currencies = poloniex.api_query_list('/currencies')
    for asset_data in currencies:
        for poloniex_asset, _ in asset_data.items():
            try:
                _ = asset_from_poloniex(poloniex_asset)
            except UnsupportedAsset:
                assert poloniex_asset in UNSUPPORTED_POLONIEX_ASSETS
            except UnknownAsset as e:
                test_warnings.warn(UserWarning(
                    f'Found unknown asset {e.identifier} in Poloniex. Support for it has to be added',  # noqa: E501
                ))


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_poloniex_query_balances_unknown_asset(function_scope_poloniex):
    """Test that if a poloniex balance query returns unknown asset no exception
    is raised and a warning is generated. Same for unsupported assets"""
    poloniex = function_scope_poloniex

    def mock_unknown_asset_return(url, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, POLONIEX_BALANCES_RESPONSE)

    with patch.object(poloniex.session, 'get', side_effect=mock_unknown_asset_return):
        # Test that after querying the assets only ETH and BTC are there
        balances, msg = poloniex.query_balances()

    assert msg == ''
    assert len(balances) == 2
    assert balances[A_BTC].amount == FVal('5.5')
    assert balances[A_BTC].usd_value == FVal('8.25')
    assert balances[A_ETH].amount == FVal('11.0')
    assert balances[A_ETH].usd_value == FVal('16.5')

    warnings = poloniex.msg_aggregator.consume_warnings()
    assert len(warnings) == 2
    assert 'unknown poloniex asset IDONTEXIST' in warnings[0]
    assert 'unsupported poloniex asset CNOTE' in warnings[1]


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_poloniex_deposits_withdrawal_unknown_asset(function_scope_poloniex):
    """Test that if a poloniex asset movement query returns unknown asset no exception
    is raised and a warning is generated. Same for unsupported assets"""
    poloniex = function_scope_poloniex

    def mock_api_return(url, **kwargs):  # pylint: disable=unused-argument
        response = MockResponse(
            200,
            POLONIEX_MOCK_DEPOSIT_WITHDRAWALS_RESPONSE,
        )
        return response

    with patch.object(poloniex.session, 'get', side_effect=mock_api_return):
        # Test that after querying the api only ETH and BTC assets are there
        asset_movements = poloniex.query_online_deposits_withdrawals(
            start_ts=0,
            end_ts=1488994442,
        )
    assert_poloniex_asset_movements(to_check_list=asset_movements, deserialized=False)

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

    def mock_api_return(url, **kwargs):  # pylint: disable=unused-argument
        response = MockResponse(
            200,
            '{"withdrawals": [{"currency": "FAC", "timestamp": 1478994442, '
            '"amount": "100.5", "fee": null, "withdrawalRequestsId": 1, "address": "131rdg5Rzn6BFufnnQaHhVa5ZtRU1J2EZR", "status": "COMPLETED"}], "deposits": []}',  # noqa: E501
        )
        return response

    with patch.object(poloniex.session, 'get', side_effect=mock_api_return):
        asset_movements = poloniex.query_online_deposits_withdrawals(
            start_ts=0,
            end_ts=1488994442,
        )

    assert len(asset_movements) == 1
    assert asset_movements[0].category == AssetMovementCategory.WITHDRAWAL
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

        def mock_api_return(url, **kwargs):  # pylint: disable=unused-argument
            return MockResponse(200, given_movements)

        with patch.object(poloniex.session, 'get', side_effect=mock_api_return):
            asset_movements = poloniex.query_online_deposits_withdrawals(
                start_ts=0,
                end_ts=1488994442,
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
    "amount": "100.5", "fee": "0.1", "withdrawalRequestsId": 1, "status": "COMPLETE", "address": "131rdg5Rzn6BFufnnQaHhVa5ZtRU1J2EZR"}], "deposits": []}"""  # noqa: E501
    check_permutations_of_input_invalid_data(input_withdrawals)
    input_deposits = """
    {"deposits": [{"currency": "FAC", "timestamp": 1478994442,
    "amount": "100.5", "depositNumber": 1, "txid": "0xfoo", "address": "0xboo"}], "withdrawals": []}"""  # noqa: E501
    check_permutations_of_input_invalid_data(input_deposits)
