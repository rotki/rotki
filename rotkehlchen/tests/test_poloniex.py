import os
from unittest.mock import patch

from rotkehlchen.assets.converters import UNSUPPORTED_POLONIEX_ASSETS, asset_from_poloniex
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.errors import UnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.order_formatting import Trade, TradeType
from rotkehlchen.poloniex import Poloniex, trade_from_poloniex
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.user_messages import MessagesAggregator


def test_trade_from_poloniex():
    amount = FVal(613.79427133)
    rate = FVal(0.00022999)
    perc_fee = FVal(0.0015)
    cost = amount * rate
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

    trade = trade_from_poloniex(poloniex_trade, 'BTC_ETH')

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

    def first_trades(currencyPair, start, end):  # pylint: disable=unused-argument
        return {'BTC': [{'data': 1}]}

    def second_trades(currencyPair, start, end):  # pylint: disable=unused-argument
        return {'BTC': [{'data': 2}]}

    messages_aggregator = MessagesAggregator()
    end_ts = 99999999999
    first_user_dir = os.path.join(data_dir, 'first')
    os.mkdir(first_user_dir)
    second_user_dir = os.path.join(data_dir, 'second')
    os.mkdir(second_user_dir)
    a = Poloniex(b'', b'', first_user_dir, messages_aggregator)
    with patch.object(a, 'returnTradeHistory', side_effect=first_trades):
        result1 = a.query_trade_history(0, end_ts, end_ts)

    b = Poloniex(b'', b'', second_user_dir, messages_aggregator)
    with patch.object(b, 'returnTradeHistory', side_effect=second_trades):
        result2 = b.query_trade_history(0, end_ts, end_ts)

    assert result1['BTC'][0]['data'] == 1
    assert result2['BTC'][0]['data'] == 2


def test_poloniex_assets_are_known(poloniex):
    currencies = poloniex.returnCurrencies()
    for poloniex_asset in currencies.keys():
        try:
            _ = asset_from_poloniex(poloniex_asset)
        except UnsupportedAsset:
            assert poloniex_asset in UNSUPPORTED_POLONIEX_ASSETS


def test_poloniex_query_balances_unnown_asset(poloniex):
    """Test that if a poloniex balance query returns unknown asset no exception
    is raised and a warning is generated."""
    def mock_unknown_asset_return(url):  # pylint: disable=unused-argument
        response = MockResponse(
            200,
            """
            {
            'BTC': {'available': '5.0', 'onOrders': '0.5'},
            'ETH': {'available': '10.0', 'onOrders': '1.0'},
            'IDONTEXIST': {'available': '1.0', 'onOrders': '2.0'},
            """)
        return response

    with patch.object(poloniex.session, 'get', side_effect=mock_unknown_asset_return):
        # Test that after querying the assets only ETH and BTC are there
        balances, msg = poloniex.query_balances()

    assert msg == ''
    assert len(balances) == 2
    assert balances[A_BTC]['amount'] == FVal('5.5')
    assert balances[A_ETH]['amount'] == FVal('11.0')

    warnings = poloniex.msg_aggregator.consume_warnings()
    assert len(warnings) == 2
    assert 'unsupported/unknown poloniex asset IDONTEXIST' in warnings[0]
