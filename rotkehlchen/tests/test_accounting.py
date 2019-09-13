import pytest

from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.accounting import accounting_history_process
from rotkehlchen.tests.utils.constants import A_DASH
from rotkehlchen.tests.utils.history import prices

DUMMY_ADDRESS = '0x0'
DUMMY_HASH = '0x0'

history1 = [
    {
        'timestamp': 1446979735,
        'pair': 'BTC_EUR',
        'trade_type': 'buy',
        'rate': 268.678317859,
        'fee': 0,
        'fee_currency': 'BTC',
        'amount': 82,
        'location': 'external',
    }, {
        'timestamp': 1446979735,
        'pair': 'ETH_EUR',
        'trade_type': 'buy',
        'rate': 0.2315893,
        'fee': 0,
        'fee_currency': 'ETH',
        'amount': 1450,
        'location': 'external',
    }, {
        'timestamp': 1473505138,  # cryptocompare hourly BTC/EUR price: 556.435
        'pair': 'ETH_BTC',  # cryptocompare hourly ETH/EUR price: 10.365
        'trade_type': 'buy',  # Buy ETH with BTC
        'rate': 0.01858275,
        'fee': 0.06999999999999999,
        'fee_currency': 'ETH',
        'amount': 50.0,
        'location': 'poloniex',
    }, {
        'timestamp': 1475042230,  # cryptocompare hourly BTC/EUR price: 537.805
        'pair': 'ETH_BTC',  # cryptocompare hourly ETH/EUR price: 11.925
        'trade_type': 'sell',  # Sell ETH for BTC
        'rate': 0.02209898,
        'fee': 0.00082871175,
        'fee_currency': 'BTC',
        'amount': 25.0,
        'location': 'poloniex',
    },
]

history_unknown_assets = [
    {
        'timestamp': 1446979735,
        'pair': 'UNKNOWNASSET_ETH',
        'trade_type': 'buy',
        'rate': 268.678317859,
        'fee': 0,
        'fee_currency': 'UNKNOWNASSET',
        'amount': 82,
        'location': 'kraken',
    },
]


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_simple_accounting(accountant):
    accounting_history_process(accountant, 1436979735, 1495751688, history1)
    assert accountant.general_trade_pl.is_close("557.528104903")
    assert accountant.taxable_trade_pl.is_close("557.528104903")


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_simple_accounting_with_unknown_and_unsupported_assets(accountant):
    """Make sure that if for some reason in the action processing we get an
    unknown asset a warning is logged and we don't crash.

    Note though that if this happens probably something wrong happened in the
    history creation as the unknown/unsupported assets should have been filtered
    out then"""
    history = history1 + history_unknown_assets
    accounting_history_process(accountant, 1436979735, 1495751688, history)
    assert accountant.general_trade_pl.is_close("557.528104903")
    assert accountant.taxable_trade_pl.is_close("557.528104903")
    warnings = accountant.msg_aggregator.consume_warnings()
    assert len(warnings) == 1
    assert 'found a trade containing unknown asset UNKNOWNASSET. Ignoring it.' in warnings[0]


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_selling_crypto_bought_with_crypto(accountant):
    history = [{
        'timestamp': 1446979735,
        'pair': 'BTC_EUR',
        'trade_type': 'buy',
        'rate': 268.678317859,
        'fee': 0,
        'fee_currency': 'BTC',
        'amount': 82,
        'location': 'external',
    }, {
        'timestamp': 1449809536,  # cryptocompare hourly BTC/EUR price: 386.175
        'pair': 'XMR_BTC',  # cryptocompare hourly XMR/EUR price: 0.396987900
        'trade_type': 'buy',  # Buy XMR with BTC
        'rate': 0.0010275,
        'fee': 0.9375,
        'fee_currency': 'XMR',
        'amount': 375,
        'location': 'poloniex',
    }, {
        'timestamp': 1458070370,  # cryptocompare hourly rate XMR/EUR price: 1.0443027675
        'pair': 'XMR_EUR',
        'trade_type': 'sell',  # Sell XMR for EUR
        'rate': 1.0443027675,
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


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_buying_selling_eth_before_daofork(accountant):
    history3 = [
        {
            'timestamp': 1446979735,  # 11/08/2015
            'pair': 'ETH_EUR',
            'trade_type': 'buy',
            'rate': 0.2315893,
            'fee': 0,
            'fee_currency': 'ETH',
            'amount': 1450,
            'location': 'external',
        }, {  # selling ETH prefork should also reduce our ETC amount
            'timestamp': 1461021812,  # 18/04/2016 (taxable)
            'pair': 'ETH_EUR',  # cryptocompare hourly ETC/EUR price: 7.88
            'trade_type': 'sell',
            'rate': 7.88,
            'fee': 0.5215,
            'fee_currency': 'EUR',
            'amount': 50,
            'location': 'kraken',
        }, {  # sell ETC after the fork
            'timestamp': 1481979135,  # 17/12/2016
            'pair': 'ETC_EUR',  # cryptocompare hourly ETC/EUR price: 1.78
            'trade_type': 'sell',  # not-taxable -- considered bought with ETH so after year
            'rate': 1.78,
            'fee': 0.9375,
            'fee_currency': 'EUR',
            'amount': 550,
            'location': 'kraken',
        }, {  # selling ETH after fork should not affect ETC amount
            'timestamp': 1482138141,  # 19/12/2016
            'pair': 'ETH_EUR',  # cryptocompare hourly ETC/EUR price: 7.45
            'trade_type': 'sell',  # not taxable after 1 year
            'rate': 7.45,
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


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_buying_selling_btc_before_bchfork(accountant):
    history = [{
        'timestamp': 1491593374,  # 04/07/2017
        'pair': 'BTC_EUR',
        'trade_type': 'buy',
        'rate': 1128.905,
        'fee': 0.55,
        'fee_currency': 'EUR',
        'amount': 6.5,
        'location': 'external',
    }, {  # selling BTC prefork should also reduce the BCH equivalent -- taxable
        'timestamp': 1500595200,  # 21/07/2017
        'pair': 'BTC_EUR',
        'trade_type': 'sell',
        'rate': 2380.835,
        'fee': 0.15,
        'fee_currency': 'EUR',
        'amount': 0.5,
        'location': 'external',
    }, {  # selling BCH after the fork -- taxable
        'timestamp': 1512693374,  # 08/12/2017
        'pair': 'BCH_EUR',  # cryptocompare hourly BCH/EUR price: 995.935
        'trade_type': 'sell',
        'rate': 995.935,
        'fee': 0.26,
        'fee_currency': 'EUR',
        'amount': 2.1,
        'location': 'kraken',
    }, {
        'timestamp': 1514937600,  # 03/01/2018
        'pair': 'BTC_EUR',  # cryptocompare hourly BCH/EUR price: 995.935
        'trade_type': 'sell',
        'rate': 12404.88,
        'fee': 0.52,
        'fee_currency': 'EUR',
        'amount': 1.2,
        'location': 'kraken',
    }]
    accounting_history_process(accountant, 1436979735, 1519693374, history)

    amount_bch = FVal(3.9)
    amount_btc = FVal(4.8)
    buys = accountant.events.events['BCH'].buys
    assert len(buys) == 1
    assert buys[0].amount == amount_bch
    assert buys[0].timestamp == 1491593374
    assert buys[0].rate == FVal('1128.905')
    assert buys[0].fee_rate.is_close(FVal('0.0846153846154'))
    assert accountant.get_calculated_asset_amount('BCH') == amount_bch
    assert accountant.get_calculated_asset_amount('BTC') == amount_btc

    assert accountant.general_trade_pl.is_close("13876.6464615")
    assert accountant.taxable_trade_pl.is_close("13876.6464615")


history5 = history1 + [{
    'timestamp': 1512693374,  # cryptocompare hourly BTC/EUR price: 537.805
    'pair': 'BTC_EUR',  # cryptocompare hourly ETH/EUR price: 11.925
    'trade_type': 'sell',
    'rate': 13503.35,
    'fee': 0,
    'fee_currency': 'BTC',
    'amount': 20.0,
    'location': 'kraken',
}]


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('accounting_include_crypto2crypto', [False])
def test_nocrypto2crypto(accountant):
    accounting_history_process(accountant, 1436979735, 1519693374, history5)
    assert accountant.general_trade_pl.is_close("264693.43364282")
    assert accountant.taxable_trade_pl.is_close("0")


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('accounting_taxfree_after_period', [None])
def test_no_taxfree_period(accountant):
    accounting_history_process(accountant, 1436979735, 1519693374, history5)
    assert accountant.general_trade_pl.is_close("265250.961748")
    assert accountant.taxable_trade_pl.is_close("265250.961748")


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('accounting_taxfree_after_period', [86400])
def test_big_taxfree_period(accountant):
    accounting_history_process(accountant, 1436979735, 1519693374, history5)
    assert accountant.general_trade_pl.is_close("265250.961748")
    assert accountant.taxable_trade_pl.is_close("0")


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_buy_event_creation(accountant):
    history = [{
        'timestamp': 1476979735,
        'pair': 'BTC_EUR',
        'trade_type': 'buy',
        'rate': 578.505,
        'fee': 0.0012,
        'fee_currency': 'BTC',
        'amount': 5,
        'location': 'kraken',
    }, {
        'timestamp': 1476979735,
        'pair': 'BTC_EUR',
        'trade_type': 'buy',
        'rate': 578.505,
        'fee': 0.0012,
        'fee_currency': 'EUR',
        'amount': 5,
        'location': 'kraken',
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


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('accounting_include_gas_costs', [False])
@pytest.mark.parametrize('accounting_ignored_assets', [[A_DASH]])
def test_not_include_gas_costs(accountant):
    """
    Added ignored assets here only to have a test for
    https://github.com/rotkehlchenio/rotkehlchen/issues/399
    """
    history = [{
        'timestamp': 1476979735,
        'pair': 'BTC_EUR',
        'trade_type': 'buy',
        'rate': 578.505,
        'fee': 0.0012,
        'fee_currency': 'BTC',
        'amount': 5,
        'location': 'kraken',
    }, {
        'timestamp': 1496979735,
        'pair': 'BTC_EUR',
        'trade_type': 'sell',
        'rate': 2519.62,
        'fee': 0.02,
        'fee_currency': 'EUR',
        'amount': 1,
        'location': 'kraken',
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


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('accounting_ignored_assets', [[A_DASH]])
def test_ignored_assets(accountant):
    history = history1 + [{
        'timestamp': 1476979735,
        'pair': 'DASH_EUR',
        'trade_type': 'buy',
        'rate': 9.76775956284,
        'fee': 0.0011,
        'fee_currency': 'DASH',
        'amount': 10,
        'location': 'kraken',
    }, {
        'timestamp': 1496979735,
        'pair': 'DASH_EUR',
        'trade_type': 'sell',
        'rate': 128.09,
        'fee': 0.015,
        'fee_currency': 'EUR',
        'amount': 5,
        'location': 'kraken',
    }]
    result = accounting_history_process(accountant, 1436979735, 1519693374, history)
    assert FVal(result['overview']['total_taxable_profit_loss']).is_close("557.528104903")


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_settlement_buy(accountant):
    history = [{
        'timestamp': 1476979735,
        'pair': 'BTC_EUR',
        'trade_type': 'buy',
        'rate': 578.505,
        'fee': 0.0012,
        'fee_currency': 'BTC',
        'amount': 5,
        'location': 'kraken',
    }, {  # 0.0079275 * 810.49 + 0.15 * 12.4625608386372145 = 8.29454360079
        'timestamp': 1484629704,  # 17/01/2017
        'pair': 'DASH_BTC',  # DASH/EUR price: 12.4625608386372145
        'trade_type': 'settlement_buy',  # Buy DASH with BTC to settle. Essentially BTC loss
        'rate': 0.015855,  # BTC/EUR price: 810.49
        'fee': 0.15,
        'fee_currency': 'DASH',
        'amount': 0.5,
        'location': 'poloniex',
    }, {
        'timestamp': 1496979735,
        'pair': 'BTC_EUR',
        'trade_type': 'sell',
        'rate': 2519.62,
        'fee': 0.02,
        'fee_currency': 'EUR',
        'amount': 1,
        'location': 'kraken',
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


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_margin_events_affect_gained_lost_amount(accountant):
    history = [{
        'timestamp': 1476979735,
        'pair': 'BTC_EUR',
        'trade_type': 'buy',
        'rate': 578.505,
        'fee': 0.0012,
        'fee_currency': 'BTC',
        'amount': 5,
        'location': 'kraken',
    }, {  # 2519.62-0.02-((0.0012*578.505)/5 + 578.505)
        'timestamp': 1496979735,
        'pair': 'BTC_EUR',
        'trade_type': 'sell',
        'rate': 2519.62,
        'fee': 0.02,
        'fee_currency': 'EUR',
        'amount': 1,
        'location': 'kraken',
    }]
    margin_history = [MarginPosition(
        location='poloniex',  # BTC/EUR: 810.49
        open_time=1484438400,  # 15/01/2017
        close_time=1484629704,  # 17/01/2017
        profit_loss=FVal('-0.5'),
        pl_currency=A_BTC,
        fee=FVal('0.001'),
        fee_currency=A_BTC,
        notes='margin1',
    ), MarginPosition(
        location='poloniex',  # BTC/EUR: 979.39
        open_time=1487116800,  # 15/02/2017
        close_time=1487289600,  # 17/02/2017
        profit_loss=FVal('0.25'),
        pl_currency=A_BTC,
        fee=FVal('0.001'),
        fee_currency=A_BTC,
        notes='margin2',
    )]

    result = accounting_history_process(
        accountant,
        1436979735,
        1519693374,
        history,
        margin_list=margin_history,
    )
    assert accountant.get_calculated_asset_amount('BTC').is_close('3.748')
    assert FVal(result['overview']['general_trade_profit_loss']).is_close('1940.9561588')
    assert FVal(result['overview']['margin_positions_profit_loss']).is_close('-162.18738')
    assert FVal(result['overview']['total_taxable_profit_loss']).is_close('1778.7687788')


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_no_corresponding_buy_for_sell(accountant):
    history = [{
        'timestamp': 1496979735,
        'pair': 'BTC_EUR',
        'trade_type': 'sell',
        'rate': 2519.62,
        'fee': 0.02,
        'fee_currency': 'EUR',
        'amount': 1,
        'location': 'kraken',
    }]

    result = accounting_history_process(
        accountant,
        1436979735,
        1519693374,
        history,
    )
    assert FVal(result['overview']['general_trade_profit_loss']).is_close('2519.6')
    assert FVal(result['overview']['total_taxable_profit_loss']).is_close('2519.6')


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_accounting_works_for_empty_history(accountant):
    history = []

    result = accounting_history_process(
        accountant,
        1436979735,
        1519693374,
        history,
    )
    assert FVal(result['overview']['general_trade_profit_loss']).is_close('0')
    assert FVal(result['overview']['total_taxable_profit_loss']).is_close('0')
