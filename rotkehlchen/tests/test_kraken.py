from copy import deepcopy
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_kraken
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.errors import UnprocessableTradePair
from rotkehlchen.fval import FVal
from rotkehlchen.kraken import KRAKEN_ASSETS, kraken_to_world_pair
from rotkehlchen.order_formatting import Trade
from rotkehlchen.tests.utils.history import TEST_END_TS
from rotkehlchen.utils.misc import ts_now


def test_coverage_of_kraken_balances(kraken):
    all_assets = set(kraken.query_public('Assets').keys())
    diff = set(KRAKEN_ASSETS).symmetric_difference(all_assets)
    assert len(diff) == 0, (
        f"Our known assets don't match kraken's assets. Difference: {diff}"
    )
    # Make sure all assets are covered by our from and to functions
    for kraken_asset in all_assets:
        asset = asset_from_kraken(kraken_asset)
        assert asset.to_kraken() == kraken_asset


def test_querying_balances(kraken):
    result, error_or_empty = kraken.query_balances()
    assert error_or_empty == ''
    assert isinstance(result, dict)
    for name, entry in result.items():
        # Make sure this does not fail
        Asset(name)
        assert 'usd_value' in entry
        assert 'amount' in entry


def test_querying_trade_history(kraken):
    now = ts_now()
    result = kraken.query_trade_history(
        start_ts=1451606400,
        end_ts=now,
        end_at_least_ts=now,
    )
    assert isinstance(result, list)
    assert len(result) != 0

    for kraken_trade in result:
        assert isinstance(kraken_trade, Trade)


def test_querying_deposits_withdrawals(kraken):
    now = ts_now()
    result = kraken.query_trade_history(
        start_ts=1451606400,
        end_ts=now,
        end_at_least_ts=now,
    )
    assert isinstance(result, list)
    assert len(result) != 0


def test_kraken_to_world_pair():
    assert kraken_to_world_pair('QTUMXBT') == 'QTUM_BTC'
    assert kraken_to_world_pair('ADACAD') == 'ADA_CAD'
    assert kraken_to_world_pair('BCHUSD') == 'BCH_USD'
    assert kraken_to_world_pair('DASHUSD') == 'DASH_USD'
    assert kraken_to_world_pair('XTZETH') == 'XTZ_ETH'
    assert kraken_to_world_pair('XXBTZGBP.d') == 'BTC_GBP'

    with pytest.raises(UnprocessableTradePair):
        kraken_to_world_pair('GABOOBABOO')


def test_find_fiat_price(kraken):
    """
    Testing that find_fiat_price works correctly

    Also regression test for https://github.com/rotkehlchenio/rotkehlchen/issues/323
    """
    kraken.first_connection()
    # A single YEN should cost less than 1 bitcoin
    jpy_price = kraken.find_fiat_price('ZJPY')
    assert jpy_price < FVal('1')

    # Kraken fees have no value
    assert kraken.find_fiat_price('KFEE') == FVal('0')


def test_kraken_query_balances_unknown_asset(function_scope_kraken):
    """Test that if a kraken balance query returns unknown asset no exception
    is raised and a warning is generated"""
    kraken = function_scope_kraken
    kraken.random_balance_data = False
    balances, msg = kraken.query_balances()

    assert msg == ''
    assert len(balances) == 2
    assert balances[A_BTC]['amount'] == FVal('5.0')
    assert balances[A_ETH]['amount'] == FVal('10.0')

    warnings = kraken.msg_aggregator.consume_warnings()
    assert len(warnings) == 1
    assert 'unsupported/unknown kraken asset NOTAREALASSET' in warnings[0]


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_kraken_query_deposit_withdrawals_unknown_asset(function_scope_kraken):
    """Test that if a kraken deposits_withdrawals query returns unknown asset
    no exception is raised and a warning is generated"""
    kraken = function_scope_kraken
    kraken.random_ledgers_data = False

    movements = kraken.query_deposits_withdrawals(
        start_ts=1408994442,
        end_ts=1498994442,
        end_at_least_ts=1498994442,
    )

    assert len(movements) == 4
    assert movements[0].asset == A_BTC
    assert movements[0].amount == FVal('5.0')
    assert movements[0].category == 'deposit'
    assert movements[1].asset == A_ETH
    assert movements[1].amount == FVal('10.0')
    assert movements[1].category == 'deposit'
    assert movements[2].asset == A_BTC
    assert movements[2].amount == FVal('5.0')
    assert movements[2].category == 'withdrawal'
    assert movements[3].asset == A_ETH
    assert movements[3].amount == FVal('10.0')
    assert movements[3].category == 'withdrawal'

    warnings = kraken.msg_aggregator.consume_warnings()
    assert len(warnings) == 2
    assert 'unknown kraken asset IDONTEXIST' in warnings[0]
    assert 'unknown kraken asset IDONTEXISTEITHER' in warnings[1]


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_trade_from_kraken_unexpected_data(function_scope_kraken):
    """Test that getting unexpected data from kraken leads to skipping the trade
    and does not lead to a crash"""
    kraken = function_scope_kraken
    kraken.random_trade_data = False
    kraken.random_ledgers_data = False
    kraken.cache_ttl_secs = 0

    # Important: Testing with a time floating point that has other than zero after decimal
    TEST_TRADES = """{
        "trades": {
            "1": {
                "ordertxid": "1",
                "postxid": 1,
                "pair": "XXBTZEUR",
                "time": "1458994442.2353",
                "type": "buy",
                "ordertype": "market",
                "price": "100",
                "vol": "1",
                "fee": "0.1",
                "cost": "100",
                "margin": "0.0",
                "misc": ""
            }
        },
        "count": 1
    }"""

    def query_kraken_and_test(input_trades, expected_warnings_num, expected_errors_num):
        with patch(target, new=input_trades):
            trades = kraken.query_trade_history(
                start_ts=0,
                end_ts=TEST_END_TS,
                end_at_least_ts=TEST_END_TS,
            )

        if expected_warnings_num == 0 and expected_errors_num == 0:
            assert len(trades) == 1
            assert trades[0].pair == 'BTC_EUR'
        else:
            assert len(trades) == 0
        errors = kraken.msg_aggregator.consume_errors()
        warnings = kraken.msg_aggregator.consume_warnings()
        assert len(errors) == expected_errors_num
        assert len(warnings) == expected_warnings_num

    # First a normal trade should have no problems
    target = 'rotkehlchen.tests.fixtures.exchanges.kraken.KRAKEN_SPECIFIC_TRADES_HISTORY_RESPONSE'
    query_kraken_and_test(TEST_TRADES, expected_warnings_num=0, expected_errors_num=0)

    # From here and on let's check trades with unexpected data
    input_trades = TEST_TRADES
    input_trades = input_trades.replace('"pair": "XXBTZEUR"', '"pair": "aadda"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    input_trades = TEST_TRADES
    input_trades = input_trades.replace('"time": "1458994442.0000"', '"time": "dsdsad"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    input_trades = TEST_TRADES
    input_trades = input_trades.replace('"vol": "1"', '"vol": "dsdsad"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    input_trades = TEST_TRADES
    input_trades = input_trades.replace('"cost": "100"', '"cost": null')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    input_trades = TEST_TRADES
    input_trades = input_trades.replace('"fee": "0.1"', '"fee": "dsdsad"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    input_trades = TEST_TRADES
    input_trades = input_trades.replace('"type": "buy"', '"type": "not existing type"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    input_trades = TEST_TRADES
    input_trades = input_trades.replace('"price": "100"', '"price": "dsadsda"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    # Also test key error
    input_trades = TEST_TRADES
    input_trades = input_trades.replace('"vol": "1",', '')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)
