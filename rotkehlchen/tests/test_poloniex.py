import os
from unittest.mock import patch

from rotkehlchen.fval import FVal
from rotkehlchen.order_formatting import Trade
from rotkehlchen.poloniex import Poloniex, trade_from_poloniex


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
    assert trade.trade_type == 'sell'
    assert trade.rate == rate
    assert trade.amount == amount
    assert trade.pair == 'ETH_BTC'
    assert trade.fee == cost * perc_fee
    assert trade.fee_currency == 'BTC'
    assert trade.location == 'poloniex'


def test_query_trade_history_not_shared_cache(data_dir):
    """Test that having 2 different poloniex instances does not use same cache

    Regression test for https://github.com/rotkehlchenio/rotkehlchen/issues/232
    We are using poloniex as an example here. Essentially tests all exchange caches.
    """

    def first_trades(currencyPair, start, end):
        return {'BTC': [{'data': 1}]}

    def second_trades(currencyPair, start, end):
        return {'BTC': [{'data': 2}]}

    end_ts = 99999999999
    first_user_dir = os.path.join(data_dir, 'first')
    os.mkdir(first_user_dir)
    second_user_dir = os.path.join(data_dir, 'second')
    os.mkdir(second_user_dir)
    a = Poloniex(b'', b'', None, first_user_dir)
    with patch.object(a, 'returnTradeHistory', side_effect=first_trades):
        result1 = a.query_trade_history(0, end_ts, end_ts)

    b = Poloniex(b'', b'', None, second_user_dir)
    with patch.object(b, 'returnTradeHistory', side_effect=second_trades):
        result2 = b.query_trade_history(0, end_ts, end_ts)

    assert result1['BTC'][0]['data'] == 1
    assert result2['BTC'][0]['data'] == 2
