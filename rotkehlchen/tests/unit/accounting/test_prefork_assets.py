import pytest

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_BCH, A_BSV, A_BTC, A_ETC, A_ETH, A_EUR
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.accounting import accounting_history_process, check_pnls_and_csv
from rotkehlchen.tests.utils.history import prices
from rotkehlchen.tests.utils.messages import no_message_errors
from rotkehlchen.types import Location, TradeType


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('ignored_assets', [[A_ETC], []])
@pytest.mark.parametrize('db_settings', [{'include_fees_in_cost_basis': False}])
def test_buying_selling_eth_before_daofork(accountant, ignored_assets, google_service):
    history3 = [
        Trade(
            timestamp=1446979735,  # 11/08/2015
            location=Location.EXTERNAL,
            base_asset=A_ETH,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=FVal(1450),
            rate=FVal('0.2315893'),
            fee=None,
            fee_currency=None,
            link=None,
        ), Trade(  # selling ETH prefork should also reduce our ETC amount
            timestamp=1461021812,  # 18/04/2016 (taxable)
            location=Location.KRAKEN,
            base_asset=A_ETH,  # cryptocompare hourly ETC/EUR price: 7.88
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=FVal(50),
            rate=FVal('7.88'),
            fee=FVal('0.5215'),
            fee_currency=A_EUR,
            link=None,
        ), Trade(  # selling ETC after the fork
            timestamp=1481979135,  # 17/12/2016
            location=Location.KRAKEN,
            base_asset=A_ETC,  # cryptocompare hourly ETC/EUR price: 7.88
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,  # not-taxable -- considered bought with ETH so after year
            amount=FVal(550),
            rate=FVal('1.78'),
            fee=FVal('0.9375'),
            fee_currency=A_EUR,
            link=None,
        ), Trade(  # selling ETH after the fork
            timestamp=1482138141,  # 19/12/2016
            location=Location.KRAKEN,
            base_asset=A_ETH,  # cryptocompare hourly ETH/EUR price: 7.45
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,  # not-taxable -- after 1 year
            amount=FVal(10),
            rate=FVal('7.45'),
            fee=FVal('0.12'),
            fee_currency=A_EUR,
            link=None,
        ),
    ]
    accounting_history_process(accountant, 1436979735, 1495751688, history3)
    no_message_errors(accountant.msg_aggregator)
    expected_etc_amount = FVal(850) if len(ignored_assets) == 0 else None
    # make sure that the intermediate ETH sell before the fork reduced our ETC if not ignored
    assert accountant.pots[0].cost_basis.get_calculated_asset_amount('ETC') == expected_etc_amount
    assert accountant.pots[0].cost_basis.get_calculated_asset_amount('ETH') == FVal(1390)

    if len(ignored_assets) == 0:
        expected_pnls = PnlTotals({
            AccountingEventType.TRADE: PNL(taxable=FVal('382.4205350'), free=FVal('923.8099920')),
            AccountingEventType.FEE: PNL(taxable=FVal('-1.579'), free=ZERO),
        })
    else:  # ignoring ETC
        expected_pnls = PnlTotals({
            AccountingEventType.TRADE: PNL(taxable=FVal('382.4205350'), free=FVal('72.1841070')),
            AccountingEventType.FEE: PNL(taxable=FVal('-0.6415'), free=ZERO),
        })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings', [{'include_fees_in_cost_basis': False}])
def test_buying_selling_btc_before_bchfork(accountant, google_service):
    history = [
        Trade(
            timestamp=1491593374,  # 04/07/2017
            location=Location.EXTERNAL,
            base_asset=A_BTC,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=FVal('6.5'),
            rate=FVal('1128.905'),
            fee=FVal('0.55'),
            fee_currency=A_EUR,
            link=None,
        ), Trade(  # selling BTC prefork should also reduce the BCH equivalent -- taxable
            timestamp=1500595200,  # 21/07/2017
            location=Location.EXTERNAL,
            base_asset=A_BTC,
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=FVal('0.5'),
            rate=FVal('2380.835'),
            fee=FVal('0.15'),
            fee_currency=A_EUR,
            link=None,
        ), Trade(   # selling BCH after the fork -- taxable
            timestamp=1512693374,  # 08/12/2017
            location=Location.KRAKEN,
            base_asset=A_BCH,  # cryptocompare hourly BCH/EUR price: 995.935
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=FVal('2.1'),
            rate=FVal('995.935'),
            fee=FVal('0.26'),
            fee_currency=A_EUR,
            link=None,
        ), Trade(
            timestamp=1514937600,  # 03/01/2018
            location=Location.KRAKEN,
            base_asset=A_BTC,  # cryptocompare hourly BCH/EUR price: 995.935
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=FVal('1.2'),
            rate=FVal('12404.88'),
            fee=FVal('0.52'),
            fee_currency=A_EUR,
            link=None,
        ),
    ]

    accounting_history_process(accountant, 1436979735, 1519693374, history)
    no_message_errors(accountant.msg_aggregator)
    amount_bch = FVal(3.9)
    amount_btc = FVal(4.8)
    buys = accountant.pots[0].cost_basis.get_events(A_BCH).acquisitions_manager.get_acquisitions()
    assert len(buys) == 1
    assert buys[0].remaining_amount == amount_bch
    assert buys[0].timestamp == 1491593374
    assert buys[0].rate.is_close('1128.905')
    assert accountant.pots[0].cost_basis.get_calculated_asset_amount(A_BCH) == amount_bch
    assert accountant.pots[0].cost_basis.get_calculated_asset_amount(A_BTC) == amount_btc

    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=FVal('13877.898'), free=ZERO),
        AccountingEventType.FEE: PNL(taxable=FVal('-1.48'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings', [{'include_fees_in_cost_basis': False}])
def test_buying_selling_bch_before_bsvfork(accountant, google_service):
    history = [
        Trade(  # 6.5 BTC 6.5 BCH 6.5 BSV
            timestamp=1491593374,  # 04/07/2017
            location=Location.EXTERNAL,
            base_asset=A_BTC,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=FVal('6.5'),
            rate=FVal('1128.905'),
            fee=FVal('0.55'),
            fee_currency=A_EUR,
            link=None,
        ), Trade(  # selling BTC prefork should also reduce the BCH and BSV equivalent -- taxable
            # 6 BTC 6 BCH 6 BSV
            timestamp=1500595200,  # 21/07/2017
            location=Location.EXTERNAL,
            base_asset=A_BTC,
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=FVal('0.5'),
            rate=FVal('2380.835'),
            fee=FVal('0.15'),
            fee_currency=A_EUR,
            link=None,
        ), Trade(  # selling BCH after the fork should also reduce BSV equivalent -- taxable
            # 6 BTC 3.9 BCH 3.9 BSV
            timestamp=1512693374,  # 08/12/2017
            location=Location.KRAKEN,
            base_asset=A_BCH,  # cryptocompare hourly BCH/EUR price: 995.935
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=FVal('2.1'),
            rate=FVal('995.935'),
            fee=FVal('0.26'),
            fee_currency=A_EUR,
            link=None,
        ), Trade(  # 4.8 BTC 3.9 BCH 3.9 BSV
            timestamp=1514937600,  # 03/01/2018
            location=Location.KRAKEN,
            base_asset=A_BTC,  # cryptocompare hourly BCH/EUR price: 995.935
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=FVal('1.2'),
            rate=FVal('12404.88'),
            fee=FVal('0.52'),
            fee_currency=A_EUR,
            link=None,
        ), Trade(  # buying BCH before the BSV fork should increase BSV equivalent
            # 4.8 BTC 4.9 BCH 4.9 BSV
            timestamp=1524937600,
            location=Location.KRAKEN,
            base_asset=A_BCH,  # cryptocompare hourly BCH/EUR price: 1146.98
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=ONE,
            rate=FVal('1146.98'),
            fee=FVal('0.52'),
            fee_currency=A_EUR,
            link=None,
        ), Trade(   # selling BCH before the BSV fork should decrease the BSV equivalent
            # 4.8 BTC 4.6 BCH 4.6 BSV
            timestamp=1525937600,
            location=Location.KRAKEN,
            base_asset=A_BCH,  # cryptocompare hourly BCH/EUR price: 1146.98
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=FVal('0.3'),
            rate=FVal('1272.05'),
            fee=FVal('0.52'),
            fee_currency=A_EUR,
            link=None,
        ), Trade(   # selling BCH after the BSV fork should not affect the BSV equivalent
            # 4.8 BTC 4.1 BCH 4.6 BSV
            timestamp=1552304352,
            location=Location.KRAKEN,
            base_asset=A_BCH,  # cryptocompare hourly BCH/EUR price: 114.27
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=FVal('0.5'),
            rate=FVal('114.27'),
            fee=FVal('0.52'),
            fee_currency=A_EUR,
            link=None,
        ),
    ]

    accounting_history_process(accountant, 1436979735, 1569693374, history)
    no_message_errors(accountant.msg_aggregator)
    amount_btc = FVal(4.8)
    amount_bch = FVal(4.1)
    amount_bsv = FVal(4.6)
    bch_buys = accountant.pots[0].cost_basis.get_events(A_BCH).acquisitions_manager.get_acquisitions()  # noqa: E501
    assert len(bch_buys) == 2
    assert sum(x.remaining_amount for x in bch_buys) == amount_bch
    assert bch_buys[0].timestamp == 1491593374
    assert bch_buys[1].timestamp == 1524937600
    bsv_buys = accountant.pots[0].cost_basis.get_events(A_BSV).acquisitions_manager.get_acquisitions()  # noqa: E501
    assert len(bsv_buys) == 2
    assert sum(x.remaining_amount for x in bsv_buys) == amount_bsv
    assert bsv_buys[0].timestamp == 1491593374
    assert bsv_buys[1].timestamp == 1524937600
    assert accountant.pots[0].cost_basis.get_calculated_asset_amount(A_BCH) == amount_bch
    assert accountant.pots[0].cost_basis.get_calculated_asset_amount(A_BTC) == amount_btc
    assert accountant.pots[0].cost_basis.get_calculated_asset_amount(A_BSV) == amount_bsv
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(
            taxable=FVal('13877.898'),
            free=FVal('-464.374'),
        ),
        AccountingEventType.FEE: PNL(taxable=FVal('-3.04'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)
