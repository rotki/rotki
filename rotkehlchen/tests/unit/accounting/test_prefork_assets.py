
import pytest

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_BCH, A_BSV, A_BTC, A_ETC, A_ETH, A_EUR
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.swap import create_swap_events
from rotkehlchen.tests.utils.accounting import (
    accounting_history_process,
    check_pnls_and_csv,
    get_calculated_asset_amount,
)
from rotkehlchen.tests.utils.history import prices
from rotkehlchen.tests.utils.messages import no_message_errors
from rotkehlchen.types import AssetAmount, Location, TimestampMS


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('ignored_assets', [[A_ETC], []])
@pytest.mark.parametrize('db_settings', [{'include_fees_in_cost_basis': False}])
def test_buying_selling_eth_before_daofork(accountant, ignored_assets, google_service):
    history3 = create_swap_events(
        timestamp=TimestampMS(1446979735000),  # 11/08/2015
        location=Location.EXTERNAL,
        event_identifier='1xyz',
        spend=AssetAmount(asset=A_EUR, amount=FVal('0.2315893') * FVal(1450)),
        receive=AssetAmount(asset=A_ETH, amount=FVal(1450)),
    ) + create_swap_events(  # selling ETH prefork should also reduce our ETC amount
        timestamp=TimestampMS(1461021812000),  # 18/04/2016 (taxable)
        location=Location.KRAKEN,
        event_identifier='2xyz',
        spend=AssetAmount(asset=A_ETH, amount=FVal(50)),  # cryptocompare hourly ETC/EUR price: 7.88  # noqa: E501
        receive=AssetAmount(asset=A_EUR, amount=FVal('7.88') * FVal(50)),
        fee=AssetAmount(asset=A_EUR, amount=FVal('0.5215')),
    ) + create_swap_events(  # selling ETC after the fork
        timestamp=TimestampMS(1481979135000),  # 17/12/2016
        location=Location.KRAKEN,
        event_identifier='3xyz',
        spend=AssetAmount(asset=A_ETC, amount=FVal(550)),  # cryptocompare hourly ETC/EUR price: 7.88  # noqa: E501
        receive=AssetAmount(asset=A_EUR, amount=FVal('1.78') * FVal(550)),
        fee=AssetAmount(asset=A_EUR, amount=FVal('0.9375')),
    ) + create_swap_events(  # selling ETH after the fork
        timestamp=TimestampMS(1482138141000),  # 19/12/2016
        location=Location.KRAKEN,
        event_identifier='4xyz',
        spend=AssetAmount(asset=A_ETH, amount=FVal(10)),  # cryptocompare hourly ETH/EUR price: 7.45  # noqa: E501
        receive=AssetAmount(asset=A_EUR, amount=FVal('7.45') * FVal(10)),
        fee=AssetAmount(asset=A_EUR, amount=FVal('0.12')),
    )
    accounting_history_process(accountant, 1436979735, 1495751688, history3)
    no_message_errors(accountant.msg_aggregator)
    expected_etc_amount = FVal(850) if len(ignored_assets) == 0 else None
    # make sure that the intermediate ETH sell before the fork reduced our ETC if not ignored
    assert get_calculated_asset_amount(accountant.pots[0].cost_basis, A_ETC) == expected_etc_amount
    assert get_calculated_asset_amount(accountant.pots[0].cost_basis, A_ETH) == FVal(1390)

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
    history = create_swap_events(
        timestamp=TimestampMS(1491593374000),  # 04/07/2017
        location=Location.EXTERNAL,
        event_identifier='1xyz',
        spend=AssetAmount(asset=A_EUR, amount=FVal('1128.905') * FVal('6.5')),
        receive=AssetAmount(asset=A_BTC, amount=FVal('6.5')),
        fee=AssetAmount(asset=A_EUR, amount=FVal('0.55')),
    ) + create_swap_events(  # selling BTC prefork should also reduce the BCH equivalent -- taxable
        timestamp=TimestampMS(1500595200000),  # 21/07/2017
        location=Location.EXTERNAL,
        event_identifier='2xyz',
        spend=AssetAmount(asset=A_BTC, amount=FVal('0.5')),
        receive=AssetAmount(asset=A_EUR, amount=FVal('2380.835') * FVal('0.5')),
        fee=AssetAmount(asset=A_EUR, amount=FVal('0.15')),
    ) + create_swap_events(  # selling BCH after the fork -- taxable
        timestamp=TimestampMS(1512693374000),  # 08/12/2017
        location=Location.KRAKEN,
        event_identifier='3xyz',
        spend=AssetAmount(asset=A_BCH, amount=FVal('2.1')),  # cryptocompare hourly BCH/EUR price: 995.935  # noqa: E501
        receive=AssetAmount(asset=A_EUR, amount=FVal('995.935') * FVal('2.1')),
        fee=AssetAmount(asset=A_EUR, amount=FVal('0.26')),
    ) + create_swap_events(
        timestamp=TimestampMS(1514937600000),  # 03/01/2018
        location=Location.KRAKEN,
        event_identifier='4xyz',
        spend=AssetAmount(asset=A_BTC, amount=FVal('1.2')),  # cryptocompare hourly BCH/EUR price: 995.935  # noqa: E501
        receive=AssetAmount(asset=A_EUR, amount=FVal('12404.88') * FVal('1.2')),
        fee=AssetAmount(asset=A_EUR, amount=FVal('0.52')),
    )

    accounting_history_process(accountant, 1436979735, 1519693374, history)
    no_message_errors(accountant.msg_aggregator)
    amount_bch = FVal(3.9)
    amount_btc = FVal(4.8)
    buys = accountant.pots[0].cost_basis.get_events(A_BCH).acquisitions_manager.get_acquisitions()
    assert len(buys) == 1
    assert buys[0].remaining_amount == amount_bch
    assert buys[0].timestamp == 1491593374
    assert buys[0].rate.is_close('1128.905')
    assert get_calculated_asset_amount(accountant.pots[0].cost_basis, A_BCH) == amount_bch
    assert get_calculated_asset_amount(accountant.pots[0].cost_basis, A_BTC) == amount_btc

    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=FVal('13877.898'), free=ZERO),
        AccountingEventType.FEE: PNL(taxable=FVal('-1.48'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings', [{'include_fees_in_cost_basis': False}])
def test_buying_selling_bch_before_bsvfork(accountant, google_service):
    history = create_swap_events(  # 6.5 BTC 6.5 BCH 6.5 BSV
        timestamp=TimestampMS(1491593374000),  # 04/07/2017
        location=Location.EXTERNAL,
        event_identifier='1xyz',
        spend=AssetAmount(asset=A_EUR, amount=FVal('1128.905') * FVal('6.5')),
        receive=AssetAmount(asset=A_BTC, amount=FVal('6.5')),
        fee=AssetAmount(asset=A_EUR, amount=FVal('0.55')),
    ) + create_swap_events(  # selling BTC prefork should also reduce the BCH and BSV equivalent -- taxable  # noqa: E501
        # 6 BTC 6 BCH 6 BSV
        timestamp=TimestampMS(1500595200000),  # 21/07/2017
        location=Location.EXTERNAL,
        event_identifier='2xyz',
        spend=AssetAmount(asset=A_BTC, amount=FVal('0.5')),
        receive=AssetAmount(asset=A_EUR, amount=FVal('2380.835') * FVal('0.5')),
        fee=AssetAmount(asset=A_EUR, amount=FVal('0.15')),
    ) + create_swap_events(  # selling BCH after the fork should also reduce BSV equivalent -- taxable  # noqa: E501
        # 6 BTC 3.9 BCH 3.9 BSV
        timestamp=TimestampMS(1512693374000),  # 08/12/2017
        location=Location.KRAKEN,
        event_identifier='3xyz',
        spend=AssetAmount(asset=A_BCH, amount=FVal('2.1')),  # cryptocompare hourly BCH/EUR price: 995.935  # noqa: E501
        receive=AssetAmount(asset=A_EUR, amount=FVal('995.935') * FVal('2.1')),
        fee=AssetAmount(asset=A_EUR, amount=FVal('0.26')),
    ) + create_swap_events(  # 4.8 BTC 3.9 BCH 3.9 BSV
        timestamp=TimestampMS(1514937600000),  # 03/01/2018
        location=Location.KRAKEN,
        event_identifier='4xyz',
        spend=AssetAmount(asset=A_BTC, amount=FVal('1.2')),  # cryptocompare hourly BCH/EUR price: 995.935  # noqa: E501
        receive=AssetAmount(asset=A_EUR, amount=FVal('12404.88') * FVal('1.2')),
        fee=AssetAmount(asset=A_EUR, amount=FVal('0.52')),
    ) + create_swap_events(  # buying BCH before the BSV fork should increase BSV equivalent
        # 4.8 BTC 4.9 BCH 4.9 BSV
        timestamp=TimestampMS(1524937600000),
        location=Location.KRAKEN,
        event_identifier='5xyz',
        spend=AssetAmount(asset=A_EUR, amount=FVal('1146.98') * ONE),
        receive=AssetAmount(asset=A_BCH, amount=ONE),  # cryptocompare hourly BCH/EUR price: 1146.98  # noqa: E501
        fee=AssetAmount(asset=A_EUR, amount=FVal('0.52')),
    ) + create_swap_events(  # selling BCH before the BSV fork should decrease the BSV equivalent
        # 4.8 BTC 4.6 BCH 4.6 BSV
        timestamp=TimestampMS(1525937600000),
        location=Location.KRAKEN,
        event_identifier='6xyz',
        spend=AssetAmount(asset=A_BCH, amount=FVal('0.3')),  # cryptocompare hourly BCH/EUR price: 1146.98  # noqa: E501
        receive=AssetAmount(asset=A_EUR, amount=FVal('1272.05') * FVal('0.3')),
        fee=AssetAmount(asset=A_EUR, amount=FVal('0.52')),
    ) + create_swap_events(  # selling BCH after the BSV fork should not affect the BSV equivalent
        # 4.8 BTC 4.1 BCH 4.6 BSV
        timestamp=TimestampMS(1552304352000),
        location=Location.KRAKEN,
        event_identifier='7xyz',
        spend=AssetAmount(asset=A_BCH, amount=FVal('0.5')),  # cryptocompare hourly BCH/EUR price: 114.27  # noqa: E501
        receive=AssetAmount(asset=A_EUR, amount=FVal('114.27') * FVal('0.5')),
        fee=AssetAmount(asset=A_EUR, amount=FVal('0.52')),
    )

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
    assert get_calculated_asset_amount(accountant.pots[0].cost_basis, A_BCH) == amount_bch
    assert get_calculated_asset_amount(accountant.pots[0].cost_basis, A_BTC) == amount_btc
    assert get_calculated_asset_amount(accountant.pots[0].cost_basis, A_BSV) == amount_bsv
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(
            taxable=FVal('13877.898'),
            free=FVal('-464.374'),
        ),
        AccountingEventType.FEE: PNL(taxable=FVal('-3.04'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)
