from rotkehlchen.fval import FVal
from rotkehlchen.order_formatting import Trade
from rotkehlchen.poloniex import trade_from_poloniex


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
    assert trade.type == 'sell'
    assert trade.rate == rate
    assert trade.amount == amount
    assert trade.cost == cost
    assert trade.cost_currency == 'BTC'
    assert trade.fee == cost * perc_fee
    assert trade.fee_currency == 'BTC'
    assert trade.location == 'poloniex'
