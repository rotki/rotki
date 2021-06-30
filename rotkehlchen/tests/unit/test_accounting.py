import pytest

from rotkehlchen.accounting.structures import AssetBalance, Balance, DefiEvent, DefiEventType
from rotkehlchen.chain.ethereum.structures import AaveInterestEvent
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_BCH, A_BSV, A_BTC, A_ETH, A_WBTC
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.accounting import accounting_history_process
from rotkehlchen.tests.utils.constants import A_DASH
from rotkehlchen.tests.utils.history import prices
from rotkehlchen.typing import AssetMovementCategory, EthereumTransaction, Fee, Location, Timestamp
from rotkehlchen.utils.misc import timestamp_to_date

DUMMY_ADDRESS = '0x0'
DUMMY_HASH = b''

history1 = [
    {
        'timestamp': 1446979735,
        'base_asset': 'BTC',
        'quote_asset': 'EUR',
        'trade_type': 'buy',
        'rate': 268.678317859,
        'fee': 0,
        'fee_currency': 'BTC',
        'amount': 82,
        'location': 'external',
    }, {
        'timestamp': 1446979735,
        'base_asset': 'ETH',
        'quote_asset': 'EUR',
        'trade_type': 'buy',
        'rate': 0.2315893,
        'fee': 0,
        'fee_currency': 'ETH',
        'amount': 1450,
        'location': 'external',
    }, {
        'timestamp': 1473505138,  # cryptocompare hourly BTC/EUR price: 556.435
        'base_asset': 'ETH',  # cryptocompare hourly ETH/EUR price: 10.36
        'quote_asset': 'BTC',
        'trade_type': 'buy',  # Buy ETH with BTC
        'rate': 0.01858275,
        'fee': 0.06999999999999999,
        'fee_currency': 'ETH',
        'amount': 50.0,
        'location': 'poloniex',
    }, {
        'timestamp': 1475042230,  # cryptocompare hourly BTC/EUR price: 537.805
        'base_asset': 'ETH',  # cryptocompare hourly ETH/EUR price: 11.925
        'quote_asset': 'BTC',
        'trade_type': 'sell',  # Sell ETH for BTC
        'rate': 0.02209898,
        'fee': 0.00082871175,
        'fee_currency': 'BTC',
        'amount': 25.0,
        'location': 'poloniex',
    },
]


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_simple_accounting(accountant):
    accounting_history_process(accountant, 1436979735, 1495751688, history1)
    assert accountant.general_trade_pl.is_close('558.25365490257463')
    assert accountant.taxable_trade_pl.is_close('558.25365490257463')


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_selling_crypto_bought_with_crypto(accountant):
    history = [{
        'timestamp': 1446979735,
        'base_asset': 'BTC',
        'quote_asset': 'EUR',
        'trade_type': 'buy',
        'rate': 268.678317859,
        'fee': 0,
        'fee_currency': 'BTC',
        'amount': 82,
        'location': 'external',
    }, {
        'timestamp': 1449809536,  # cryptocompare hourly BTC/EUR price: 386.175
        'base_asset': 'XMR',  # cryptocompare hourly XMR/EUR price: 0.39665
        'quote_asset': 'BTC',
        'trade_type': 'buy',  # Buy XMR with BTC
        'rate': 0.0010275,
        'fee': 0.9375,
        'fee_currency': 'XMR',
        'amount': 375,
        'location': 'poloniex',
    }, {
        'timestamp': 1458070370,  # cryptocompare hourly rate XMR/EUR price: 1.0443027675
        'base_asset': 'XMR',
        'quote_asset': 'EUR',
        'trade_type': 'sell',  # Sell XMR for EUR
        'rate': 1.0443027675,
        'fee': 0.117484061344,
        'fee_currency': 'EUR',
        'amount': 45,
        'location': 'kraken',
    }]
    accounting_history_process(accountant, 1436979735, 1495751688, history)
    # Make sure buying XMR with BTC also creates a BTC sell
    sells = accountant.events.cost_basis.get_events(A_BTC).spends
    assert len(sells) == 1
    assert sells[0].amount == FVal('0.3853125')
    assert sells[0].timestamp == 1449809536
    assert sells[0].rate.is_close(FVal('386.0340632603'))
    assert sells[0].fee_rate == Fee(ZERO)  # the fee should not be double counted
    assert sells[0].gain.is_close(FVal('148.74375'))

    assert accountant.general_trade_pl.is_close('74.1943864386100625')
    assert accountant.taxable_trade_pl.is_close('74.1943864386100625')


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_buying_selling_eth_before_daofork(accountant):
    history3 = [
        {
            'timestamp': 1446979735,  # 11/08/2015
            'base_asset': 'ETH',
            'quote_asset': 'EUR',
            'trade_type': 'buy',
            'rate': 0.2315893,
            'fee': 0,
            'fee_currency': 'ETH',
            'amount': 1450,
            'location': 'external',
        }, {  # selling ETH prefork should also reduce our ETC amount
            'timestamp': 1461021812,  # 18/04/2016 (taxable)
            'base_asset': 'ETH',  # cryptocompare hourly ETC/EUR price: 7.88
            'quote_asset': 'EUR',
            'trade_type': 'sell',
            'rate': 7.88,
            'fee': 0.5215,
            'fee_currency': 'EUR',
            'amount': 50,
            'location': 'kraken',
        }, {  # sell ETC after the fork
            'timestamp': 1481979135,  # 17/12/2016
            'base_asset': 'ETC',  # cryptocompare hourly ETC/EUR price: 1.78
            'quote_asset': 'EUR',
            'trade_type': 'sell',  # not-taxable -- considered bought with ETH so after year
            'rate': 1.78,
            'fee': 0.9375,
            'fee_currency': 'EUR',
            'amount': 550,
            'location': 'kraken',
        }, {  # selling ETH after fork should not affect ETC amount
            'timestamp': 1482138141,  # 19/12/2016
            'base_asset': 'ETH',  # cryptocompare hourly ETC/EUR price: 7.45
            'quote_asset': 'EUR',
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
    assert accountant.events.cost_basis.get_calculated_asset_amount('ETC') == FVal(850)
    assert accountant.events.cost_basis.get_calculated_asset_amount('ETH') == FVal(1390)
    assert accountant.general_trade_pl.is_close('1304.651527')
    assert accountant.taxable_trade_pl.is_close('381.899035')


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_buying_selling_btc_before_bchfork(accountant):
    history = [{
        'timestamp': 1491593374,  # 04/07/2017
        'base_asset': 'BTC',
        'quote_asset': 'EUR',
        'trade_type': 'buy',
        'rate': 1128.905,
        'fee': 0.55,
        'fee_currency': 'EUR',
        'amount': 6.5,
        'location': 'external',
    }, {  # selling BTC prefork should also reduce the BCH equivalent -- taxable
        'timestamp': 1500595200,  # 21/07/2017
        'base_asset': 'BTC',
        'quote_asset': 'EUR',
        'trade_type': 'sell',
        'rate': 2380.835,
        'fee': 0.15,
        'fee_currency': 'EUR',
        'amount': 0.5,
        'location': 'external',
    }, {  # selling BCH after the fork -- taxable
        'timestamp': 1512693374,  # 08/12/2017
        'base_asset': 'BCH',  # cryptocompare hourly BCH/EUR price: 995.935
        'quote_asset': 'EUR',
        'trade_type': 'sell',
        'rate': 995.935,
        'fee': 0.26,
        'fee_currency': 'EUR',
        'amount': 2.1,
        'location': 'kraken',
    }, {
        'timestamp': 1514937600,  # 03/01/2018
        'base_asset': 'BTC',  # cryptocompare hourly BCH/EUR price: 995.935
        'quote_asset': 'EUR',
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
    buys = accountant.events.cost_basis.get_events(A_BCH).acquisitions
    assert len(buys) == 1
    assert buys[0].remaining_amount == amount_bch
    assert buys[0].timestamp == 1491593374
    assert buys[0].rate == FVal('1128.905')
    assert buys[0].fee_rate.is_close(FVal('0.0846153846154'))
    assert accountant.events.cost_basis.get_calculated_asset_amount(A_BCH) == amount_bch
    assert accountant.events.cost_basis.get_calculated_asset_amount(A_BTC) == amount_btc

    assert accountant.general_trade_pl.is_close('13876.6464615')
    assert accountant.taxable_trade_pl.is_close('13876.6464615')


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_buying_selling_bch_before_bsvfork(accountant):
    history = [{
        # 6.5 BTC 6.5 BCH 6.5 BSV
        'timestamp': 1491593374,  # 04/07/2017
        'base_asset': 'BTC',
        'quote_asset': 'EUR',
        'trade_type': 'buy',
        'rate': 1128.905,
        'fee': 0.55,
        'fee_currency': 'EUR',
        'amount': 6.5,
        'location': 'external',
    }, {  # selling BTC pre both fork should also reduce the BCH and BSV equivalent -- taxable
        # 6 BTC 6 BCH 6 BSV
        'timestamp': 1500595200,  # 21/07/2017
        'base_asset': 'BTC',
        'quote_asset': 'EUR',
        'trade_type': 'sell',
        'rate': 2380.835,
        'fee': 0.15,
        'fee_currency': 'EUR',
        'amount': 0.5,
        'location': 'external',
    }, {  # selling BCH after the fork should also reduce BSV equivalent -- taxable
        # 6 BTC 3.9 BCH 3.9 BSV
        'timestamp': 1512693374,  # 08/12/2017
        'base_asset': 'BCH',  # cryptocompare hourly BCH/EUR price: 995.935
        'quote_asset': 'EUR',
        'trade_type': 'sell',
        'rate': 995.935,
        'fee': 0.26,
        'fee_currency': 'EUR',
        'amount': 2.1,
        'location': 'kraken',
    }, {
        # 4.8 BTC 3.9 BCH 3.9 BSV
        'timestamp': 1514937600,  # 03/01/2018
        'base_asset': 'BTC',  # cryptocompare hourly BCH/EUR price: 995.935
        'quote_asset': 'EUR',
        'trade_type': 'sell',
        'rate': 12404.88,
        'fee': 0.52,
        'fee_currency': 'EUR',
        'amount': 1.2,
        'location': 'kraken',
    }, {  # buying BCH before the BSV fork should increase BSV equivalent
        # 4.8 BTC 4.9 BCH 4.9 BSV
        'timestamp': 1524937600,
        'base_asset': 'BCH',  # cryptocompare hourly BCH/EUR price: 1146.98
        'quote_asset': 'EUR',
        'trade_type': 'buy',
        'rate': 1146.98,
        'fee': 0.52,
        'fee_currency': 'EUR',
        'amount': 1,
        'location': 'kraken',
    }, {  # selling BCH before the BSV fork should decrease the BSV equivalent
        # 4.8 BTC 4.6 BCH 4.6 BSV
        'timestamp': 1525937600,
        'base_asset': 'BCH',  # cryptocompare hourly BCH/EUR price: 1146.98
        'quote_asset': 'EUR',
        'trade_type': 'sell',
        'rate': 1272.05,
        'fee': 0.52,
        'fee_currency': 'EUR',
        'amount': 0.3,
        'location': 'kraken',
    }, {  # selling BCH after the BSV fork should not affect the BSV equivalent
        # 4.8 BTC 4.1 BCH 4.6 BSV
        'timestamp': 1552304352,
        'base_asset': 'BCH',  # cryptocompare hourly BCH/EUR price: 114.27
        'quote_asset': 'EUR',
        'trade_type': 'sell',
        'rate': 114.27,
        'fee': 0.52,
        'fee_currency': 'EUR',
        'amount': 0.5,
        'location': 'kraken',
    }]
    accounting_history_process(accountant, 1436979735, 1569693374, history)

    amount_btc = FVal(4.8)
    amount_bch = FVal(4.1)
    amount_bsv = FVal(4.6)
    bch_buys = accountant.events.cost_basis.get_events(A_BCH).acquisitions
    assert len(bch_buys) == 2
    assert sum(x.remaining_amount for x in bch_buys) == amount_bch
    assert bch_buys[0].timestamp == 1491593374
    assert bch_buys[1].timestamp == 1524937600
    bsv_buys = accountant.events.cost_basis.get_events(A_BSV).acquisitions
    assert len(bsv_buys) == 2
    assert sum(x.remaining_amount for x in bsv_buys) == amount_bsv
    assert bsv_buys[0].timestamp == 1491593374
    assert bsv_buys[1].timestamp == 1524937600
    assert accountant.events.cost_basis.get_calculated_asset_amount(A_BCH) == amount_bch
    assert accountant.events.cost_basis.get_calculated_asset_amount(A_BTC) == amount_btc
    assert accountant.events.cost_basis.get_calculated_asset_amount(A_BSV) == amount_bsv

    assert accountant.general_trade_pl.is_close('13411.164769')
    assert accountant.taxable_trade_pl.is_close('13876.646461')


history5 = history1 + [{
    'timestamp': 1512693374,  # cryptocompare hourly BTC/EUR price: 537.805
    'base_asset': 'BTC',  # cryptocompare hourly ETH/EUR price: 11.925
    'quote_asset': 'EUR',
    'trade_type': 'sell',
    'rate': 13503.35,
    'fee': 0,
    'fee_currency': 'BTC',
    'amount': 20.0,
    'location': 'kraken',
}]


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings', [{
    'include_crypto2crypto': False,
}])
def test_nocrypto2crypto(accountant):
    accounting_history_process(accountant, 1436979735, 1519693374, history5)
    # Expected = 3 trades + the creation of ETC, BCH and BSV after fork times
    msg = 'The crypto to crypto trades should not appear in the list at all'
    assert len(accountant.csvexporter.all_events) == 6, msg

    assert accountant.general_trade_pl.is_close('264693.43364282')
    assert accountant.taxable_trade_pl.is_close('0')


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings', [{
    'taxfree_after_period': -1,
}])
def test_no_taxfree_period(accountant):
    accounting_history_process(accountant, 1436979735, 1519693374, history5)
    assert accountant.general_trade_pl.is_close('265251.6872977225746')
    assert accountant.taxable_trade_pl.is_close('265251.6872977225746')


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings', [{
    'taxfree_after_period': 86400,
}])
def test_big_taxfree_period(accountant):
    accounting_history_process(accountant, 1436979735, 1519693374, history5)
    assert accountant.general_trade_pl.is_close('265251.6872977225746375')
    assert accountant.taxable_trade_pl.is_close('0')


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_buy_event_creation(accountant):
    history = [{
        'timestamp': 1476979735,
        'base_asset': 'BTC',
        'quote_asset': 'EUR',
        'trade_type': 'buy',
        'rate': 578.505,
        'fee': 0.0012,
        'fee_currency': 'BTC',
        'amount': 5,
        'location': 'kraken',
    }, {
        'timestamp': 1476979735,
        'base_asset': 'BTC',
        'quote_asset': 'EUR',
        'trade_type': 'buy',
        'rate': 578.505,
        'fee': 0.0012,
        'fee_currency': 'EUR',
        'amount': 5,
        'location': 'kraken',
    }]
    accounting_history_process(accountant, 1436979735, 1519693374, history)
    buys = accountant.events.cost_basis.get_events(A_BTC).acquisitions
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
@pytest.mark.parametrize('ignored_assets', [[A_DASH]])
@pytest.mark.parametrize('db_settings', [{
    'include_gas_costs': False,
}])
def test_not_include_gas_costs(accountant):
    """
    Added ignored assets here only to have a test for
    https://github.com/rotki/rotki/issues/399
    """
    history = [{
        'timestamp': 1476979735,
        'base_asset': 'BTC',
        'quote_asset': 'EUR',
        'trade_type': 'buy',
        'rate': 578.505,
        'fee': 0.0012,
        'fee_currency': 'BTC',
        'amount': 5,
        'location': 'kraken',
    }, {
        'timestamp': 1496979735,
        'base_asset': 'BTC',
        'quote_asset': 'EUR',
        'trade_type': 'sell',
        'rate': 2519.62,
        'fee': 0.02,
        'fee_currency': 'EUR',
        'amount': 1,
        'location': 'kraken',
    }]
    eth_tx_list = [
        EthereumTransaction(
            timestamp=1491062063,  # 01/04/2017
            block_number=3458409,
            tx_hash=DUMMY_HASH,
            from_address=DUMMY_ADDRESS,
            to_address=DUMMY_ADDRESS,
            value=FVal('12323'),
            gas=FVal('5000000'),
            gas_price=FVal('2000000000'),
            gas_used=FVal('1000000'),
            input_data=DUMMY_HASH,
            nonce=0,
        ),
    ]
    result = accounting_history_process(
        accountant,
        1436979735,
        1519693374,
        history,
        eth_transaction_list=eth_tx_list,
    )
    assert FVal(result['overview']['total_taxable_profit_loss']).is_close('1940.9561588')


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('ignored_assets', [[A_DASH]])
def test_ignored_assets(accountant):
    history = history1 + [{
        'timestamp': 1476979735,
        'base_asset': 'DASH',
        'quote_asset': 'EUR',
        'trade_type': 'buy',
        'rate': 9.76775956284,
        'fee': 0.0011,
        'fee_currency': 'DASH',
        'amount': 10,
        'location': 'kraken',
    }, {
        'timestamp': 1496979735,
        'base_asset': 'DASH',
        'quote_asset': 'EUR',
        'trade_type': 'sell',
        'rate': 128.09,
        'fee': 0.015,
        'fee_currency': 'EUR',
        'amount': 5,
        'location': 'kraken',
    }]
    result = accounting_history_process(accountant, 1436979735, 1519693374, history)
    assert FVal(result['overview']['total_taxable_profit_loss']).is_close('558.253654902574637500')


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_settlement_buy(accountant):
    history = [{
        'timestamp': 1476979735,
        'base_asset': 'BTC',
        'quote_asset': 'EUR',
        'trade_type': 'buy',
        'rate': 578.505,
        'fee': 0.0012,
        'fee_currency': 'BTC',
        'amount': 5,
        'location': 'kraken',
    }, {  # 0.0079275 * 810.49 + 0.15 * 12.4625608386372145 = 8.29454360079
        'timestamp': 1484629704,  # 17/01/2017
        'base_asset': 'DASH',  # DASH/EUR price: 12.88
        'quote_asset': 'BTC',
        'trade_type': 'settlement_buy',  # Buy DASH with BTC to settle. Essentially BTC loss
        'rate': 0.015855,  # BTC/EUR price: 810.49
        'fee': 0.15,
        'fee_currency': 'DASH',
        'amount': 0.5,
        'location': 'poloniex',
    }, {
        'timestamp': 1496979735,
        'base_asset': 'BTC',
        'quote_asset': 'EUR',
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
    assert accountant.events.cost_basis.get_calculated_asset_amount('BTC').is_close('3.9908725')
    assert FVal(result['overview']['total_taxable_profit_loss']).is_close('1932.598999')
    assert FVal(result['overview']['settlement_losses']).is_close('8.357159475')


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_margin_events_affect_gained_lost_amount(accountant):
    history = [{
        'timestamp': 1476979735,
        'base_asset': 'BTC',
        'quote_asset': 'EUR',
        'trade_type': 'buy',
        'rate': 578.505,
        'fee': 0.0012,
        'fee_currency': 'BTC',
        'amount': 5,
        'location': 'kraken',
    }, {  # 2519.62-0.02-((0.0012*578.505)/5 + 578.505)
        'timestamp': 1496979735,
        'base_asset': 'BTC',
        'quote_asset': 'EUR',
        'trade_type': 'sell',
        'rate': 2519.62,
        'fee': 0.02,
        'fee_currency': 'EUR',
        'amount': 1,
        'location': 'kraken',
    }]
    margin_history = [MarginPosition(
        location=Location.POLONIEX,  # BTC/EUR: 810.49
        open_time=1484438400,  # 15/01/2017
        close_time=1484629704,  # 17/01/2017
        profit_loss=FVal('-0.5'),
        pl_currency=A_BTC,
        fee=FVal('0.001'),
        fee_currency=A_BTC,
        link='1',
        notes='margin1',
    ), MarginPosition(
        location=Location.POLONIEX,  # BTC/EUR: 979.39
        open_time=1487116800,  # 15/02/2017
        close_time=1487289600,  # 17/02/2017
        profit_loss=FVal('0.25'),
        pl_currency=A_BTC,
        fee=FVal('0.001'),
        fee_currency=A_BTC,
        link='2',
        notes='margin2',
    )]

    result = accounting_history_process(
        accountant,
        1436979735,
        1519693374,
        history,
        margin_list=margin_history,
    )
    assert accountant.events.cost_basis.get_calculated_asset_amount('BTC').is_close('3.7468')
    assert FVal(result['overview']['general_trade_profit_loss']).is_close('1940.9561588')
    assert FVal(result['overview']['margin_positions_profit_loss']).is_close('-162.18738')
    assert FVal(result['overview']['total_taxable_profit_loss']).is_close('1778.7687788')


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_no_corresponding_buy_for_sell(accountant):
    history = [{
        'timestamp': 1496979735,
        'base_asset': 'BTC',
        'quote_asset': 'EUR',
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


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings, expected', [
    ({'account_for_assets_movements': False}, 0),
    ({'account_for_assets_movements': True}, 0.57867315),
])
def test_assets_movements_not_accounted_for(accountant, expected):
    # asset_movements_list partially copied from
    # rotkehlchen/tests/integration/test_end_to_end_tax_report.py
    asset_movements_list = [AssetMovement(
        # before query period -- 8.915 * 0.001 = 8.915e-3
        location=Location.KRAKEN,
        category=AssetMovementCategory.WITHDRAWAL,
        address=None,
        transaction_id=None,
        timestamp=Timestamp(1479510304),  # 18/11/2016,
        asset=A_ETH,  # cryptocompare hourly ETH/EUR: 8.915
        amount=FVal('95'),
        fee_asset=A_ETH,
        fee=Fee(FVal('0.001')),
        link='krakenid1',
    ), AssetMovement(  # 0.00029*1964.685 = 0.56975865
        location=Location.POLONIEX,
        address='foo',
        transaction_id='0xfoo',
        category=AssetMovementCategory.WITHDRAWAL,
        timestamp=Timestamp(1495969504),  # 28/05/2017,
        asset=A_BTC,  # cryptocompare hourly BTC/EUR: 1964.685
        amount=FVal('8.5'),
        fee_asset=A_BTC,
        fee=Fee(FVal('0.00029')),
        link='poloniexid1',
    )]
    history = []

    result = accounting_history_process(
        accountant,
        1436979735,
        1519693374,
        history,
        asset_movements_list=asset_movements_list,
    )
    assert FVal(result['overview']['asset_movement_fees']).is_close(expected)
    assert FVal(result['overview']['total_taxable_profit_loss']).is_close(-expected)
    assert FVal(result['overview']['total_profit_loss']).is_close(-expected)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings', [
    {'calculate_past_cost_basis': False, 'taxfree_after_period': -1},
    {'calculate_past_cost_basis': True, 'taxfree_after_period': -1},
])
def test_not_calculate_past_cost_basis(accountant, db_settings):
    # trades copied from
    # rotkehlchen/tests/integration/test_end_to_end_tax_report.py

    history = [{
        'timestamp': 1446979735,  # 08/11/2015
        'base_asset': 'BTC',
        'quote_asset': 'EUR',
        'trade_type': 'buy',
        'rate': 268.678317859,
        'fee': 0,
        'fee_currency': 'BTC',
        'amount': 5,
        'location': 'external',
    }, {
        'timestamp': 1446979735,  # 08/11/2015
        'base_asset': 'ETH',
        'quote_asset': 'EUR',
        'trade_type': 'buy',
        'rate': 0.2315893,
        'fee': 0,
        'fee_currency': 'ETH',
        'amount': 1450,
        'location': 'external',
    }, {
        'timestamp': 1488373504,  # 29/02/2017
        'base_asset': 'BTC',
        'quote_asset': 'EUR',
        'trade_type': 'sell',
        'rate': 1146.22,
        'fee': 0.01,
        'fee_currency': 'EUR',
        'amount': 2,
        'location': 'kraken',
    }]
    result = accounting_history_process(
        accountant=accountant,
        start_ts=1466979735,
        end_ts=1519693374,
        history_list=history,
    )

    sell_gain = (
        FVal(history[-1]['rate']) * FVal(history[-1]['amount']) -
        FVal(history[-1]['fee'])
    )
    if db_settings['calculate_past_cost_basis'] is True:
        buy_cost = FVal(history[0]['rate']) * FVal(history[-1]['amount'])
        expected = sell_gain - buy_cost
    else:
        expected = sell_gain

    assert FVal(result['overview']['taxable_trade_profit_loss']).is_close(expected)
    assert FVal(result['overview']['total_taxable_profit_loss']).is_close(expected)
    assert FVal(result['overview']['total_profit_loss']).is_close(expected)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_defi_event_zero_amount(accountant):
    """Test that if a Defi Event with a zero amount obtained
    comes in we don't raise an error

    Regression test for a division by zero error a user reported
    """
    defi_events = [DefiEvent(
        timestamp=1467279735,
        wrapped_event=AaveInterestEvent(
            event_type='interest',
            asset=A_WBTC,
            value=Balance(amount=FVal(0), usd_value=FVal(0)),
            block_number=4,
            timestamp=Timestamp(1467279735),
            tx_hash='0x49c67445d26679623f9b7d56a8be260a275cb6744a1c1ae5a8d6883a5a5c03de',
            log_index=4,
        ),
        event_type=DefiEventType.AAVE_EVENT,
        got_asset=A_WBTC,
        got_balance=Balance(amount=FVal(0), usd_value=FVal(0)),
        spent_asset=A_WBTC,
        spent_balance=Balance(amount=FVal(0), usd_value=FVal(0)),
        pnl=[AssetBalance(asset=A_WBTC, balance=Balance(amount=FVal(0), usd_value=FVal(0)))],
        count_spent_got_cost_basis=True,
        tx_hash='0x49c67445d26679623f9b7d56a8be260a275cb6744a1c1ae5a8d6883a5a5c03de',
    )]
    result = accounting_history_process(
        accountant=accountant,
        start_ts=1466979735,
        end_ts=1519693374,
        history_list=[],
        defi_events_list=defi_events,
    )

    assert result['all_events'][0] == {
        'cost_basis': None,
        'is_virtual': False,
        'location': 'blockchain',
        'net_profit_or_loss': ZERO,
        'paid_asset': 'WBTC(0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599)',
        'paid_in_asset': ZERO,
        'paid_in_profit_currency': ZERO,
        'received_asset': '',
        'received_in_asset': ZERO,
        'taxable_amount': ZERO,
        'taxable_bought_cost_in_profit_currency': ZERO,
        'taxable_received_in_profit_currency': ZERO,
        'time': 1467279735,
        'type': 'defi_event',
    }


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_sell_fiat_for_crypto(accountant):
    """
    Test for https://github.com/rotki/rotki/issues/2993
    Make sure that selling fiat for crypto does not give warnings due to
    inability to trace the source of the sold fiat.
    """
    history = [{
        'timestamp': 1476979735,
        'base_asset': 'EUR',
        'quote_asset': 'BTC',
        'trade_type': 'sell',
        'rate': 0.002,
        'fee': 0.0012,
        'fee_currency': 'EUR',
        'amount': 2000,
        'location': 'kraken',
    }, {
        'timestamp': 1496979735,
        'base_asset': 'CHF',
        'quote_asset': 'ETH',
        'trade_type': 'sell',
        'rate': 0.004,
        'fee': 0.02,
        'fee_currency': 'EUR',
        'amount': 500,
        'location': 'kraken',
    }, {
        'timestamp': 1506979735,
        'base_asset': 'ETH',
        'quote_asset': 'EUR',
        'trade_type': 'sell',
        'rate': 25000,
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
    assert FVal(result['overview']['total_profit_loss']) == FVal(25000 - 0.02 - 250 * 1.001)  # the 0.02/2 fee from sell of CHF to ETH is not counted since the first sell is skipped, only the buy of ETH is counted  # noqa: E501
    assert accountant.events.cost_basis.get_calculated_asset_amount(A_ETH) == FVal(1)
    assert accountant.events.cost_basis.get_calculated_asset_amount(A_BTC) == FVal(4)
    warnings = accountant.msg_aggregator.consume_warnings()
    assert len(warnings) == 0
    errors = accountant.msg_aggregator.consume_errors()
    assert len(errors) == 0


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_fees_count_in_cost_basis(accountant):
    """
    Test for https://github.com/rotki/rotki/issues/2744
    Make sure that asset amounts used in fees are reduced.
    """
    history = [{
        'timestamp': 1609537953,
        'base_asset': 'ETH',
        'quote_asset': 'EUR',
        'trade_type': 'buy',
        'rate': 598.26,
        'fee': 1,
        'fee_currency': 'EUR',
        'amount': 1,
        'location': 'kraken',
    }, {
        'timestamp': 1624395186,
        'base_asset': 'ETH',
        'quote_asset': 'EUR',
        'trade_type': 'sell',
        'rate': 1862.06,
        'fee': 0.5,
        'fee_currency': 'ETH',
        'amount': 0.5,
        'location': 'kraken',
    }, {
        'timestamp': 1625001464,
        'base_asset': 'ETH',
        'quote_asset': 'EUR',
        'trade_type': 'sell',
        'rate': 1837.31,
        'fee': 0,
        'fee_currency': 'EUR',
        'amount': 0.5,
        'location': 'kraken',
    }]
    result = accounting_history_process(
        accountant,
        1436979735,
        1625001466,
        history,
    )

    assert FVal(result['overview']['total_profit_loss']) == FVal(
        # first sell also has a huge fee, same as the amount sold
        1862.06 * 0.5 - (0.5 * 598.26 + 0.5) - 0.5 * 1862.06 +
        # 2nd sell can't find ETH due to fee of previous so considers pure profit
        1837.31 * 0.5,
    )
    assert accountant.events.cost_basis.get_calculated_asset_amount(A_ETH) is None
    error = (
        f'No documented acquisition found for ETH(Ethereum) before '
        f'{timestamp_to_date(1625001464, treat_as_local=True)}. '
        f'Let rotki know how you acquired it via a ledger action'
    )
    warnings = accountant.msg_aggregator.consume_warnings()
    assert len(warnings) == 0
    errors = accountant.msg_aggregator.consume_errors()
    assert errors == [error]
