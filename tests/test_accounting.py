import pytest

from rotkehlchen.accounting import Accountant
from rotkehlchen.history import PriceHistorian, trades_from_dictlist
from rotkehlchen.errors import CorruptData


def init_accounting_tests(history_list, margin_list, start_ts, end_ts):
    price_historian = PriceHistorian('/home/lefteris/.rotkehlchen')
    accountant = Accountant(
        price_historian=price_historian,
        profit_currency='EUR',
        create_csv=False
    )
    accountant.process_history(
        start_ts=start_ts,
        end_ts=end_ts,
        trade_history=trades_from_dictlist(history_list, start_ts, end_ts),
        margin_history=trades_from_dictlist(margin_list, start_ts, end_ts),
        loan_history=list(),
        asset_movements=list(),
        eth_transactions=list()
    )
    return accountant


history1 = [
    {
        "timestamp": 1446979735,
        "pair": "BTC_EUR",
        "type": "buy",
        "rate": 268.678317859,
        "cost": 22031.6220644,
        "cost_currency": "EUR",
        "fee": 0,
        "fee_currency": "BTC",
        "amount": 82,
        "location": "external",
    }, {
        "timestamp": 1446979735,
        "pair": "ETH_EUR",
        "type": "buy",
        "rate": 0.2315893,
        "cost": 335.804485,
        "cost_currency": "EUR",
        "fee": 0,
        "fee_currency": "ETH",
        "amount": 1450,
        "location": "external",
    }, {
        "timestamp": 1473505138,  # cryptocompare hourly BTC/EUR price: 556.435
        "pair": "BTC_ETH",  # cryptocompare hourly ETH/EUR price: 10.365
        "type": "buy",  # Buy ETH with BTC
        "rate": 0.01858275,
        "cost": 0.9291375,
        "cost_currency": "BTC",
        "fee": 0.06999999999999999,
        "fee_currency": "ETH",
        "amount": 50.0,
        "location": "poloniex"
    }, {
        "timestamp": 1475042230,  # cryptocompare hourly BTC/EUR price: 537.805
        "pair": "BTC_ETH",  # cryptocompare hourly ETH/EUR price: 11.925
        "type": "sell",  # Sell ETH for BTC
        "rate": 0.02209898,
        "cost": 0.5524745,
        "cost_currency": "BTC",
        "fee": 0.00082871175,
        "fee_currency": "BTC",
        "amount": 25.0,
        "location": "poloniex"
    },
]


def test_simple_accounting():
    accountant = init_accounting_tests(history1, [], 1436979735, 1495751688)
    assert accountant.general_trade_profit_loss.is_close("557.528104903")
    assert accountant.taxable_trade_profit_loss.is_close("557.528104903")


bad_history1 = [
    {
        "timestamp": 1446979735,
        "pair": "BTC_EUR",
        "type": "buy",
        "rate": 268.678317859,
        "cost": 1131.6220644,
        "cost_currency": "EUR",
        "fee": 0,
        "fee_currency": "BTC",
        "amount": 82,
        "location": "external",
    }
]

bad_history2 = [
    {
        "timestamp": 1446979735,
        "pair": "BTC_EUR",
        "type": "buy",
        "rate": 268.678317859,
        "cost": 22031.6220644,
        "cost_currency": "EUR",
        "fee": 0,
        "fee_currency": "BTC",
        "amount": 82,
        "location": "external",
    }, {
        "timestamp": 1475042230,
        "pair": "BTC_ETH",
        "type": "sell",
        "rate": 0.02209898,
        "cost": 0.1524745,
        "cost_currency": "BTC",
        "fee": 0.00082871175,
        "fee_currency": "BTC",
        "amount": 25.0,
        "location": "poloniex"
    },
]


def test_mismatch_in_amount_rate_and_cost():
    with pytest.raises(CorruptData):
        init_accounting_tests(bad_history1, [], 1436979735, 1495751688)

    with pytest.raises(CorruptData):
        init_accounting_tests(bad_history2, [], 1436979735, 1495751688)


history2 = [
    {
        "timestamp": 1446979735,
        "pair": "BTC_EUR",
        "type": "buy",
        "rate": 268.678317859,
        "cost": 22031.6220644,
        "cost_currency": "EUR",
        "fee": 0,
        "fee_currency": "BTC",
        "amount": 82,
        "location": "external",
    }, {
        "timestamp": 1446979735,
        "pair": "ETH_EUR",
        "type": "buy",
        "rate": 0.2315893,
        "cost": 335.804485,
        "cost_currency": "EUR",
        "fee": 0,
        "fee_currency": "ETH",
        "amount": 1450,
        "location": "external",
    }, {
        'timestamp': 1449809536,  # cryptocompare hourly BTC/EUR price: 386.175
        'pair': 'BTC_XMR',  # cryptocompare hourly XMR/EUR price: 0.396987900
        'type': 'buy',  # Buy XMR with BTC
        'rate': 0.0010275,
        'cost': 0.3853125,
        'cost_currency': 'BTC',
        'fee': 0.9375,
        'fee_currency': 'XMR',
        'amount': 375,
        'location': 'poloniex'
    }, {
        'timestamp': 1458070370,  # cryptocompare hourly rate XMR/EUR price: 1.0443027675
        'pair': 'XMR_EUR',
        'type': 'sell',  # Sell XMR for EUR
        'rate': 1.0443027675,
        'cost': 46.9936245375,
        'cost_currency': 'EUR',
        'fee': 0.117484061344,
        'fee_currency': 'EUR',
        'amount': 45,
        'location': 'kraken'
    }
]


def test_selling_crypto_bought_with_crypto():
    accountant = init_accounting_tests(history2, [], 1436979735, 1495751688)
    assert accountant.general_trade_profit_loss.is_close("73.9657992344")
    assert accountant.taxable_trade_profit_loss.is_close("73.9657992344")
