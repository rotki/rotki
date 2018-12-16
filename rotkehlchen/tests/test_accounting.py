import pytest

from rotkehlchen.errors import CorruptData
from rotkehlchen.fval import FVal
from rotkehlchen.order_formatting import MarginPosition
from rotkehlchen.tests.utils.accounting import accounting_history_process

DUMMY_ADDRESS = '0x0'
DUMMY_HASH = '0x0'

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


def test_buying_selling_eth_before_daofork(accountant):
    history3 = [
        {
            "timestamp": 1446979735,  # 11/08/2015
            "pair": "ETH_EUR",
            "type": "buy",
            "rate": 0.2315893,
            "cost": 335.804485,
            "cost_currency": "EUR",
            "fee": 0,
            "fee_currency": "ETH",
            "amount": 1450,
            "location": "external",
        }, {  # selling ETH prefork should also reduce our ETC amount
            'timestamp': 1461021812,  # 18/04/2016 (taxable)
            'pair': 'ETH_EUR',  # cryptocompare hourly ETC/EUR price: 7.88
            'type': 'sell',
            'rate': 7.88,
            'cost': 394,
            'cost_currency': 'EUR',
            'fee': 0.5215,
            'fee_currency': 'EUR',
            'amount': 50,
            'location': 'kraken',
        }, {  # sell ETC after the fork
            'timestamp': 1481979135,  # 17/12/2016
            'pair': 'ETC_EUR',  # cryptocompare hourly ETC/EUR price: 1.78
            'type': 'sell',  # not-taxable -- considered bought with ETH so after year
            'rate': 1.78,
            'cost': 979,
            'cost_currency': 'EUR',
            'fee': 0.9375,
            'fee_currency': 'EUR',
            'amount': 550,
            'location': 'kraken',
        }, {  # selling ETH after fork should not affect ETC amount
            'timestamp': 1482138141,  # 19/12/2016
            'pair': 'ETH_EUR',  # cryptocompare hourly ETC/EUR price: 7.45
            'type': 'sell',  # not taxable after 1 year
            'rate': 7.45,
            'cost': 74.5,
            'cost_currency': 'EUR',
            'fee': 0.12,
            'fee_currency': 'EUR',
            'amount': 10,
            'location': 'kraken',
        },
    ]
    accounting_history_process(accountant, 1436979735, 1495751688, history3)
    # make sure that the intermediate ETH sell before the fork reduced our ETC
    assert accountant.get_calculated_asset_amount('ETC') == FVal(850)
    assert accountant.get_calculated_asset_amount('ETH') == FVal(1390)
    assert accountant.general_trade_pl.is_close('1304.651527')
    assert accountant.taxable_trade_pl.is_close('381.899035')


def test_buying_selling_btc_before_bchfork(accountant):
    history = [{
        "timestamp": 1491593374,  # 04/07/2017
        "pair": "BTC_EUR",
        "type": "buy",
        "rate": 1128.905,
        "cost": 7337.8825,
        "cost_currency": "EUR",
        "fee": 0.55,
        "fee_currency": "EUR",
        "amount": 6.5,
        "location": "external",
    }, {  # selling BTC prefork should also reduce the BCH equivalent -- taxable
        "timestamp": 1500595200,  # 21/07/2017
        "pair": "BTC_EUR",
        "type": "sell",
        "rate": 2380.835,
        "cost": 1190.4175,
        "cost_currency": "EUR",
        "fee": 0.15,
        "fee_currency": "EUR",
        "amount": 0.5,
        "location": "external",
    }, {  # selling BCH after the fork -- taxable
        'timestamp': 1512693374,  # 08/12/2017
        'pair': 'BCH_EUR',  # cryptocompare hourly BCH/EUR price: 995.935
        'type': 'sell',
        'rate': 995.935,
        'cost': 2091.4635,
        'cost_currency': 'EUR',
        'fee': 0.26,
        'fee_currency': 'EUR',
        'amount': 2.1,
        'location': 'kraken',
    }, {
        'timestamp': 1514937600,  # 03/01/2018
        'pair': 'BTC_EUR',  # cryptocompare hourly BCH/EUR price: 995.935
        'type': 'sell',
        'rate': 12404.88,
        'cost': 14885.856,
        'cost_currency': 'EUR',
        'fee': 0.52,
        'fee_currency': 'EUR',
        'amount': 1.2,
        'location': 'kraken',
    }]
    accounting_history_process(accountant, 1436979735, 1519693374, history)

    amount_BCH = FVal(3.9)
    amount_BTC = FVal(4.8)
    buys = accountant.events.events['BCH'].buys
    assert len(buys) == 1
    assert buys[0].amount == amount_BCH
    assert buys[0].timestamp == 1491593374
    assert buys[0].rate == FVal('1128.905')
    assert buys[0].fee_rate.is_close(FVal('0.0846153846154'))
    assert accountant.get_calculated_asset_amount('BCH') == amount_BCH
    assert accountant.get_calculated_asset_amount('BTC') == amount_BTC

    assert accountant.general_trade_pl.is_close("13876.6464615")
    assert accountant.taxable_trade_pl.is_close("13876.6464615")


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


@pytest.mark.parametrize('accounting_include_gas_costs', [False])
def test_not_include_gas_costs(accountant):
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
        "timestamp": 1496979735,
        "pair": "BTC_EUR",
        "type": "sell",
        "rate": 2519.62,
        "cost": 2519.62,
        "cost_currency": "EUR",
        "fee": 0.02,
        "fee_currency": "EUR",
        "amount": 1,
        "location": "kraken",
    }]
    eth_tx_list = [{
        'timestamp': 1491062063,  # 01/04/2017
        'block_number': 3458409,  # cryptocompare hourly ETH/EUR: 47.5
        'hash': DUMMY_HASH,
        'from_address': DUMMY_ADDRESS,
        'to_address': DUMMY_ADDRESS,
        'value': 12323,
        'gas': 5000000,
        'gas_price': 2000000000,
        'gas_used': 1000000,
    }]
    result = accounting_history_process(
        accountant,
        1436979735,
        1519693374,
        history,
        eth_transaction_list=eth_tx_list,
    )
    assert FVal(result['overview']['total_taxable_profit_loss']).is_close("1940.9561588")


@pytest.mark.parametrize('accounting_ignored_assets', [['DASH']])
def test_ignored_assets(accountant):
    history = history1 + [{
        "timestamp": 1476979735,
        "pair": "DASH_EUR",
        "type": "buy",
        "rate": 9.76775956284,
        "cost": 97.6775956284,
        "cost_currency": "EUR",
        "fee": 0.0011,
        "fee_currency": "DASH",
        "amount": 10,
        "location": "kraken",
    }, {
        "timestamp": 1496979735,
        "pair": "DASH_EUR",
        "type": "sell",
        "rate": 128.09,
        "cost": 640.45,
        "cost_currency": "EUR",
        "fee": 0.015,
        "fee_currency": "EUR",
        "amount": 5,
        "location": "kraken",
    }]
    result = accounting_history_process(accountant, 1436979735, 1519693374, history)
    assert FVal(result['overview']['total_taxable_profit_loss']).is_close("557.528104903")


def test_settlement_buy(accountant):
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
    }, {  # 0.0079275 * 810.49 + 0.15 * 12.4625608386372145 = 8.29454360079
        'timestamp': 1484629704,  # 17/01/2017
        'pair': 'BTC_DASH',  # DASH/EUR price: 12.4625608386372145
        'type': 'settlement_buy',  # Buy DASH with BTC to settle. Essentially BTC loss
        'rate': 0.015855,  # BTC/EUR price: 810.49
        'cost': 0.0079275,
        'cost_currency': 'BTC',
        'fee': 0.15,
        'fee_currency': 'DASH',
        'amount': 0.5,
        'location': 'poloniex',
    }, {
        "timestamp": 1496979735,
        "pair": "BTC_EUR",
        "type": "sell",
        "rate": 2519.62,
        "cost": 2519.62,
        "cost_currency": "EUR",
        "fee": 0.02,
        "fee_currency": "EUR",
        "amount": 1,
        "location": "kraken",
    }]

    result = accounting_history_process(
        accountant,
        1436979735,
        1519693374,
        history,
    )
    assert accountant.get_calculated_asset_amount('BTC').is_close('3.9920725')
    assert FVal(result['overview']['total_taxable_profit_loss']).is_close('1932.6616152')
    assert FVal(result['overview']['settlement_losses']).is_close('8.29454360079')


def test_margin_events_affect_gaine_lost_amount(accountant):
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
    }, {  # 2519.62-0.02-((0.0012*578.505)/5 + 578.505)
        "timestamp": 1496979735,
        "pair": "BTC_EUR",
        "type": "sell",
        "rate": 2519.62,
        "cost": 2519.62,
        "cost_currency": "EUR",
        "fee": 0.02,
        "fee_currency": "EUR",
        "amount": 1,
        "location": "kraken",
    }]
    margin_history = [MarginPosition(
        exchange='poloniex',  # BTC/EUR: 810.49
        open_time=1484438400,  # 15/01/2017
        close_time=1484629704,  # 17/01/2017
        profit_loss=FVal('-0.5'),
        pl_currency='BTC',
        notes='margin1',
    ), MarginPosition(
        exchange='poloniex',  # BTC/EUR: 979.39
        open_time=1487116800,  # 15/02/2017
        close_time=1487289600,  # 17/02/2017
        profit_loss=FVal('0.25'),
        pl_currency='BTC',
        notes='margin2',
    )]

    result = accounting_history_process(
        accountant,
        1436979735,
        1519693374,
        history,
        margin_list=margin_history,
    )
    assert accountant.get_calculated_asset_amount('BTC').is_close('3.75')
    assert FVal(result['overview']['general_trade_profit_loss']).is_close('1940.9561588')
    assert FVal(result['overview']['margin_positions_profit_loss']).is_close('-160.3975')
    assert FVal(result['overview']['total_taxable_profit_loss']).is_close('1780.5586588')
