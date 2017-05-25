from leftrader.accounting import Accountant
from leftrader.history import PriceHistorian, trades_from_dictlist
from leftrader.utils import Logger, isclose


history1 = [
    {
        "timestamp": 1446979735,
        "pair": "BTC_EUR",
        "type": "buy",
        "rate": 268.678317859,
        "cost": 22031.6220644,
        "cost_currency": "EUR",
        "fee": 0,
        "fee_currency": "ETH",
        "amount": 82,
        "location": "external",
    }, {
        "timestamp": 1446979735,
        "pair": "ETH_EUR",
        "type": "buy",
        "rate": 0.13433915893,
        "cost": 5381.0893501,
        "cost_currency": "EUR",
        "fee": 0,
        "fee_currency": "ETH",
        "amount": 40056,
        "location": "external",
    }, {
        "timestamp": 1473505138,
        "pair": "BTC_ETH",
        "type": "buy",
        "rate": 0.01858275,
        "cost": 0.9291375,
        "cost_currency": "BTC",
        "fee": 0.06999999999999999,
        "fee_currency": "ETH",
        "amount": 50.0,
        "location": "poloniex"
    }, {
        "timestamp": 1475042230,
        "pair": "BTC_ETH",
        "type": "sell",
        "rate": 0.02209898,
        "cost": 0.5524745,
        "cost_currency": "BTC",
        "fee": 0.00082871175,
        "fee_currency": "BTC",
        "amount": 25.0,
        "location": "poloniex"
    },
]


def test_simple_history1():
    price_historian = PriceHistorian('/home/lefteris/ew/leftrader/data/', {})
    logger = Logger(None, False)
    accountant = Accountant(logger, price_historian, 'EUR')
    accountant.process_history(trades_from_dictlist(history1), [], [])
    assert isclose(accountant.general_profit_loss, 562.76426759)
    assert isclose(accountant.taxable_profit_loss, 562.76426759)
