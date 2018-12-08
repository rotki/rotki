import pytest

from rotkehlchen.errors import CorruptData
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.accounting import accounting_history_process

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
        "location": "poloniex",
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
        "location": "poloniex",
    },
]


def test_simple_accounting(accountant):
    accounting_history_process(accountant, 1436979735, 1495751688, history1)
    assert accountant.general_trade_pl.is_close("557.528104903")
    assert accountant.taxable_trade_pl.is_close("557.528104903")


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
    },
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
        "location": "poloniex",
    },
]


def test_mismatch_in_amount_rate_and_cost(accountant):
    with pytest.raises(CorruptData):
        accounting_history_process(accountant, 1436979735, 1495751688, bad_history1)

    with pytest.raises(CorruptData):
        accounting_history_process(accountant, 1436979735, 1495751688, bad_history2)


def test_selling_crypto_bought_with_crypto(accountant):
    history = [{
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
        'timestamp': 1449809536,  # cryptocompare hourly BTC/EUR price: 386.175
        'pair': 'BTC_XMR',  # cryptocompare hourly XMR/EUR price: 0.396987900
        'type': 'buy',  # Buy XMR with BTC
        'rate': 0.0010275,
        'cost': 0.3853125,
        'cost_currency': 'BTC',
        'fee': 0.9375,
        'fee_currency': 'XMR',
        'amount': 375,
        'location': 'poloniex',
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
        'location': 'kraken',
    }]
    accounting_history_process(accountant, 1436979735, 1495751688, history)
    # Make sure buying XMR with BTC also creates a BTC sell
    sells = accountant.events.events['BTC'].sells
    assert len(sells) == 1
    assert sells[0].amount == FVal('0.3853125')
    assert sells[0].timestamp == 1449809536
    assert sells[0].rate == FVal('386.175')
    assert sells[0].fee_rate.is_close(FVal('0.96590729927'))
    assert sells[0].gain.is_close(FVal('148.798054688'))

    assert accountant.general_trade_pl.is_close("73.8764769569")
    assert accountant.taxable_trade_pl.is_close("73.8764769569")


history3 = [
    {
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
        'timestamp': 1481979135,
        'pair': 'ETC_EUR',  # cryptocompare hourly ETC/EUR price: 1.78
        'type': 'sell',
        'rate': 1.78,
        'cost': 979,
        'cost_currency': 'EUR',
        'fee': 0.9375,
        'fee_currency': 'EUR',
        'amount': 550,
        'location': 'kraken',
    },
]


def test_buying_eth_before_daofork(accountant):
    accounting_history_process(accountant, 1436979735, 1495751688, history3)
    assert accountant.general_trade_pl.is_close("850.688385")
    assert accountant.taxable_trade_pl.is_close("0")


def test_buying_btc_before_bchfork(accountant):
    history = [{
        "timestamp": 1491593374,
        "pair": "BTC_EUR",
        "type": "buy",
        "rate": 1128.905,
        "cost": 7337.8825,
        "cost_currency": "EUR",
        "fee": 0.55,
        "fee_currency": "EUR",
        "amount": 6.5,
        "location": "external",
    }, {
        'timestamp': 1512693374,
        'pair': 'BCH_EUR',  # cryptocompare hourly BCH/EUR price: 995.935
        'type': 'sell',
        'rate': 995.935,
        'cost': 2091.4635,
        'cost_currency': 'EUR',
        'fee': 0.26,
        'fee_currency': 'EUR',
        'amount': 2.1,
        'location': 'kraken',
    }]
    accounting_history_process(accountant, 1436979735, 1519693374, history)

    buys = accountant.events.events['BCH'].buys
    assert len(buys) == 1
    assert buys[0].amount == FVal(4.4)
    assert buys[0].timestamp == 1491593374
    assert buys[0].rate == FVal('1128.905')
    assert buys[0].fee_rate.is_close(FVal('0.0846153846154'))

    assert accountant.general_trade_pl.is_close("-279.67469231")
    assert accountant.taxable_trade_pl.is_close("-279.67469231")


history5 = history1 + [{
    "timestamp": 1512693374,  # cryptocompare hourly BTC/EUR price: 537.805
    "pair": "BTC_EUR",  # cryptocompare hourly ETH/EUR price: 11.925
    "type": "sell",
    "rate": 13503.35,
    "cost": 270067,
    "cost_currency": "EUR",
    "fee": 0,
    "fee_currency": "BTC",
    "amount": 20.0,
    "location": "kraken",
}]


@pytest.mark.parametrize('accounting_include_crypto2crypto', [False])
def test_nocrypto2crypto(accountant):
    accounting_history_process(accountant, 1436979735, 1519693374, history5)
    assert accountant.general_trade_pl.is_close("264693.43364282")
    assert accountant.taxable_trade_pl.is_close("0")


@pytest.mark.parametrize('accounting_taxfree_after_period', [None])
def test_no_taxfree_period(accountant):
    accounting_history_process(accountant, 1436979735, 1519693374, history5)
    assert accountant.general_trade_pl.is_close("265250.961748")
    assert accountant.taxable_trade_pl.is_close("265250.961748")


@pytest.mark.parametrize('accounting_taxfree_after_period', [86400])
def test_big_taxfree_period(accountant):
    accounting_history_process(accountant, 1436979735, 1519693374, history5)
    assert accountant.general_trade_pl.is_close("265250.961748")
    assert accountant.taxable_trade_pl.is_close("0")


def test_buy_event_creation(accountant):
    history = [{
        "timestamp": 1476979735,
        "pair": "BTC_EUR",
        "type": "buy",
        "rate": 578.505,
        "cost": 2892.525,
        "cost_currency": "EUR",
        "fee": 0.0012,
        "fee_currency": "BTC",
        "amount": 5,
        "location": "kraken",
    }, {
        "timestamp": 1476979735,
        "pair": "BTC_EUR",
        "type": "buy",
        "rate": 578.505,
        "cost": 2892.525,
        "cost_currency": "EUR",
        "fee": 0.0012,
        "fee_currency": "EUR",
        "amount": 5,
        "location": "kraken",
    }]
    accounting_history_process(accountant, 1436979735, 1519693374, history)
    buys = accountant.events.events['BTC'].buys
    assert len(buys) == 2
    assert buys[0].amount == FVal(5)
    assert buys[0].timestamp == 1476979735
    assert buys[0].rate == FVal('578.505')
    assert buys[0].fee_rate == FVal('0.1388412')

    assert buys[1].amount == FVal(5)
    assert buys[1].timestamp == 1476979735
    assert buys[1].rate == FVal('578.505')
    assert buys[1].fee_rate == FVal('2.4e-4')
