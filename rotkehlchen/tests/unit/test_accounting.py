import pytest

from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.accounting.structures import (
    Balance,
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import (
    A_BCH,
    A_BSV,
    A_BTC,
    A_ETC,
    A_ETH,
    A_ETH2,
    A_EUR,
    A_KFEE,
    A_USDT,
)
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.accounting import accounting_history_process, check_pnls_and_csv
from rotkehlchen.tests.utils.constants import A_CHF, A_DASH, A_XMR
from rotkehlchen.tests.utils.history import prices
from rotkehlchen.types import (
    AssetAmount,
    AssetMovementCategory,
    Fee,
    Location,
    Price,
    Timestamp,
    TradeType,
    make_evm_tx_hash,
)
from rotkehlchen.utils.misc import timestamp_to_date

DUMMY_ADDRESS = '0x0'
DUMMY_HASH = make_evm_tx_hash(b'')

history1 = [
    Trade(
        timestamp=Timestamp(1446979735),
        location=Location.EXTERNAL,
        base_asset=A_BTC,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal(82)),
        rate=Price(FVal('268.678317859')),
        fee=None,
        fee_currency=None,
        link=None,
    ), Trade(
        timestamp=Timestamp(1446979735),
        location=Location.EXTERNAL,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal(1450)),
        rate=Price(FVal('0.2315893')),
        fee=None,
        fee_currency=None,
        link=None,
    ), Trade(
        timestamp=Timestamp(1473505138),  # cryptocompare hourly BTC/EUR price: 556.435
        location=Location.POLONIEX,
        base_asset=A_ETH,  # cryptocompare hourly ETH/EUR price: 10.36
        quote_asset=A_BTC,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal(50)),
        rate=Price(FVal('0.01858275')),
        fee=Fee(FVal('0.06999999999999999')),
        fee_currency=A_ETH,
        link=None,
    ), Trade(
        timestamp=Timestamp(1475042230),  # cryptocompare hourly BTC/EUR price: 537.805
        location=Location.POLONIEX,
        base_asset=A_ETH,  # cryptocompare hourly ETH/EUR price: 11.925
        quote_asset=A_BTC,
        trade_type=TradeType.SELL,
        amount=AssetAmount(FVal(25)),
        rate=Price(FVal('0.02209898')),
        fee=Fee(FVal('0.00082871175')),
        fee_currency=A_BTC,
        link=None,
    ),
]


def _check_for_errors(accountant) -> None:
    errors = accountant.msg_aggregator.consume_errors()
    warnings = accountant.msg_aggregator.consume_warnings()
    assert len(errors) == 0, f'Found errors: {errors}'
    assert len(warnings) == 0, f'Found warnings: {warnings}'


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_simple_accounting(accountant):
    accounting_history_process(accountant, 1436979735, 1495751688, history1)
    _check_for_errors(accountant)
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=FVal('559.6947154'), free=ZERO),
        AccountingEventType.FEE: PNL(taxable=FVal('-0.23886813'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_selling_crypto_bought_with_crypto(accountant):
    history = [
        Trade(
            timestamp=1446979735,
            location=Location.EXTERNAL,
            base_asset=A_BTC,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=FVal(82),
            rate=FVal('268.678317859'),
            fee=None,
            fee_currency=None,
            link=None,
        ), Trade(
            timestamp=1449809536,  # cryptocompare hourly BTC/EUR price: 386.175
            location=Location.POLONIEX,
            base_asset=A_XMR,  # cryptocompare hourly XMR/EUR price: 0.39665
            quote_asset=A_BTC,
            trade_type=TradeType.BUY,
            amount=FVal(375),
            rate=FVal('0.0010275'),
            fee=FVal('0.9375'),
            fee_currency=A_XMR,
            link=None,
        ), Trade(
            timestamp=1458070370,  # cryptocompare hourly rate XMR/EUR price: 1.0443027675
            location=Location.KRAKEN,
            base_asset=A_XMR,
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=FVal(45),
            rate=FVal('1.0443027675'),
            fee=FVal('0.117484061344'),
            fee_currency=A_XMR,
            link=None,
        ),
    ]
    accounting_history_process(accountant, 1436979735, 1495751688, history)
    _check_for_errors(accountant)
    # Make sure buying XMR with BTC also creates a BTC sell
    sells = accountant.pots[0].cost_basis.get_events(A_BTC).spends
    assert len(sells) == 1
    assert sells[0].timestamp == 1449809536
    assert sells[0].amount.is_close(FVal('0.3853125'))
    assert sells[0].rate.is_close(FVal('386.03406326'))

    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=FVal('74.3118704999540625'), free=ZERO),
        AccountingEventType.FEE: PNL(taxable=FVal('-0.419658351381311222'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_buying_selling_eth_before_daofork(accountant):
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
    _check_for_errors(accountant)
    # make sure that the intermediate ETH sell before the fork reduced our ETC
    assert accountant.pots[0].cost_basis.get_calculated_asset_amount('ETC') == FVal(850)
    assert accountant.pots[0].cost_basis.get_calculated_asset_amount('ETH') == FVal(1390)

    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=FVal('382.4205350'), free=FVal('923.8099920')),
        AccountingEventType.FEE: PNL(taxable=FVal('-0.5215'), free=FVal('-1.0575')),
    })
    check_pnls_and_csv(accountant, expected_pnls)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_buying_selling_btc_before_bchfork(accountant):
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
    _check_for_errors(accountant)
    amount_bch = FVal(3.9)
    amount_btc = FVal(4.8)
    buys = accountant.pots[0].cost_basis.get_events(A_BCH).acquisitions
    assert len(buys) == 1
    assert buys[0].remaining_amount == amount_bch
    assert buys[0].timestamp == 1491593374
    assert buys[0].rate.is_close('1128.98961538')
    assert accountant.pots[0].cost_basis.get_calculated_asset_amount(A_BCH) == amount_bch
    assert accountant.pots[0].cost_basis.get_calculated_asset_amount(A_BTC) == amount_btc

    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=FVal('13877.57646153846153846153846'), free=ZERO),
        AccountingEventType.FEE: PNL(taxable=FVal('-1.48'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_buying_selling_bch_before_bsvfork(accountant):
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
    _check_for_errors(accountant)
    amount_btc = FVal(4.8)
    amount_bch = FVal(4.1)
    amount_bsv = FVal(4.6)
    bch_buys = accountant.pots[0].cost_basis.get_events(A_BCH).acquisitions
    assert len(bch_buys) == 2
    assert sum(x.remaining_amount for x in bch_buys) == amount_bch
    assert bch_buys[0].timestamp == 1491593374
    assert bch_buys[1].timestamp == 1524937600
    bsv_buys = accountant.pots[0].cost_basis.get_events(A_BSV).acquisitions
    assert len(bsv_buys) == 2
    assert sum(x.remaining_amount for x in bsv_buys) == amount_bsv
    assert bsv_buys[0].timestamp == 1491593374
    assert bsv_buys[1].timestamp == 1524937600
    assert accountant.pots[0].cost_basis.get_calculated_asset_amount(A_BCH) == amount_bch
    assert accountant.pots[0].cost_basis.get_calculated_asset_amount(A_BTC) == amount_btc
    assert accountant.pots[0].cost_basis.get_calculated_asset_amount(A_BSV) == amount_bsv
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(
            taxable=FVal('13877.57646153846153846153846'),
            free=FVal('-464.4416923076923076923076920'),
        ),
        AccountingEventType.FEE: PNL(taxable=FVal('-2'), free=FVal('-1.04')),
    })
    check_pnls_and_csv(accountant, expected_pnls)


history5 = history1 + [Trade(
    timestamp=Timestamp(1512693374),  # cryptocompare hourly BTC/EUR price: 537.805
    location=Location.KRAKEN,
    base_asset=A_BTC,
    quote_asset=A_EUR,
    trade_type=TradeType.SELL,
    amount=AssetAmount(FVal('20')),
    rate=Price(FVal('13503.35')),
    fee=None,
    fee_currency=None,
    link=None,
)]


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings', [{
    'include_crypto2crypto': False,
}])
def test_nocrypto2crypto(accountant):
    accounting_history_process(accountant, 1436979735, 1519693374, history5)
    _check_for_errors(accountant)
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=ZERO, free=FVal('264693.433642820')),
        AccountingEventType.FEE: PNL(taxable=FVal('-1.1708853227087498964'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings', [{
    'taxfree_after_period': -1,
}])
def test_no_taxfree_period(accountant):
    accounting_history_process(accountant, 1436979735, 1519693374, history5)
    _check_for_errors(accountant)
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=FVal('265253.1283582327833875'), free=ZERO),
        AccountingEventType.FEE: PNL(taxable=FVal('-0.238868129979988140934107'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings', [{
    'taxfree_after_period': 86400,
}])
def test_big_taxfree_period(accountant):
    accounting_history_process(accountant, 1436979735, 1519693374, history5)
    _check_for_errors(accountant)
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=ZERO, free=FVal('265253.1283582327833875')),
        AccountingEventType.FEE: PNL(taxable=ZERO, free=FVal('-0.238868129979988140934107')),
    })
    check_pnls_and_csv(accountant, expected_pnls)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_buy_event_creation(accountant):
    history = [
        Trade(
            timestamp=1476979735,
            location=Location.KRAKEN,
            base_asset=A_BTC,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=FVal(5),
            rate=FVal('578.505'),
            fee=FVal('0.0012'),
            fee_currency=A_BTC,
            link=None,
        ), Trade(
            timestamp=1476979735,
            location=Location.KRAKEN,
            base_asset=A_BTC,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=FVal(5),
            rate=FVal('578.505'),
            fee=FVal('0.0012'),
            fee_currency=A_EUR,
            link=None,
        ),
    ]
    accounting_history_process(accountant, 1436979735, 1519693374, history)
    _check_for_errors(accountant)
    buys = accountant.pots[0].cost_basis.get_events(A_BTC).acquisitions
    assert len(buys) == 2
    assert buys[0].amount == FVal(5)
    assert buys[0].timestamp == 1476979735
    assert buys[0].rate.is_close('578.6438412')  # (578.505 * 5 + 0.0012 * 578.505)/5

    assert buys[1].amount == FVal(5)
    assert buys[1].timestamp == 1476979735
    assert buys[1].rate == FVal('578.50524')  # (578.505 * 5 + 0.0012)/5


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('ignored_assets', [[A_DASH]])
@pytest.mark.parametrize('db_settings', [{'include_gas_costs': True}, {'include_gas_costs': False}])  # noqa: E501
def test_include_gas_costs(accountant):
    addr1 = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'
    tx_hash = '0x5cc0e6e62753551313412492296d5e57bea0a9d1ce507cc96aa4aa076c5bde7a'
    history = [
        Trade(
            timestamp=1539388574,
            location=Location.EXTERNAL,
            base_asset=A_ETH,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=FVal(10),
            rate=FVal('168.7'),
            fee=None,
            fee_currency=None,
            link=None,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=1569924574000,
            location=Location.BLOCKCHAIN,
            location_label=addr1,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.000030921')),
            # The no-member is due to https://github.com/PyCQA/pylint/issues/3162
            notes=f'Burned 0.000030921 ETH in gas from {addr1} for transaction {tx_hash}',
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            counterparty='gas',
        )]
    accounting_history_process(accountant, start_ts=1436979735, end_ts=1619693374, history_list=history)  # noqa: E501
    _check_for_errors(accountant)
    expected = ZERO
    expected_pnls = PnlTotals()
    if accountant.pots[0].settings.include_gas_costs:
        expected = FVal('-0.0052163727')
        expected_pnls[AccountingEventType.TRANSACTION_EVENT] = PNL(taxable=expected, free=ZERO)
    check_pnls_and_csv(accountant, expected_pnls)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('ignored_assets', [[A_DASH]])
def test_ignored_assets(accountant):
    history = history1 + [
        Trade(
            timestamp=1476979735,
            location=Location.KRAKEN,
            base_asset=A_DASH,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=FVal(10),
            rate=FVal('9.76775956284'),
            fee=FVal('0.0011'),
            fee_currency=A_DASH,
            link=None,
        ), Trade(
            timestamp=1496979735,
            location=Location.KRAKEN,
            base_asset=A_DASH,
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=FVal(5),
            rate=FVal('128.09'),
            fee=FVal('0.015'),
            fee_currency=A_EUR,
            link=None,
        ),
    ]
    accounting_history_process(accountant, 1436979735, 1519693374, history)
    _check_for_errors(accountant)
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=FVal('559.6947154127833875'), free=ZERO),
        AccountingEventType.FEE: PNL(taxable=FVal('-0.238868129979988140934107'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_margin_events_affect_gained_lost_amount(accountant):
    history = [
        Trade(
            timestamp=1476979735,
            location=Location.KRAKEN,
            base_asset=A_BTC,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=FVal(5),
            rate=FVal('578.505'),
            fee=FVal('0.0012'),
            fee_currency=A_BTC,
            link=None,
        ), Trade(  # 2519.62 - 0.02 - ((0.0012*578.505)/5 + 578.505)
            timestamp=1476979735,
            location=Location.KRAKEN,
            base_asset=A_BTC,
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=FVal(1),
            rate=FVal('2519.62'),
            fee=FVal('0.02'),
            fee_currency=A_EUR,
            link=None,
        ),
    ]
    history += [MarginPosition(
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

    accounting_history_process(
        accountant=accountant,
        start_ts=1436979735,
        end_ts=1519693374,
        history_list=history,
    )
    _check_for_errors(accountant)
    assert accountant.pots[0].cost_basis.get_calculated_asset_amount('BTC').is_close('3.7468')
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=FVal('1940.9761588'), free=ZERO),
        AccountingEventType.FEE: PNL(taxable=FVal('-1.87166029184'), free=ZERO),
        AccountingEventType.MARGIN_POSITION: PNL(taxable=FVal('-44.47442060'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_no_corresponding_buy_for_sell(accountant):
    """Test that if there is no corresponding buy for a sell, the entire sell counts as profit"""
    history = [Trade(
        timestamp=1476979735,
        location=Location.KRAKEN,
        base_asset=A_BTC,
        quote_asset=A_EUR,
        trade_type=TradeType.SELL,
        amount=FVal(1),
        rate=FVal('2519.62'),
        fee=FVal('0.02'),
        fee_currency=A_EUR,
        link=None,
    )]
    accounting_history_process(
        accountant=accountant,
        start_ts=1436979735,
        end_ts=1519693374,
        history_list=history,
    )

    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=FVal('2519.62'), free=ZERO),
        AccountingEventType.FEE: PNL(taxable=FVal('-0.02'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_accounting_works_for_empty_history(accountant):
    history = []
    accounting_history_process(
        accountant=accountant,
        start_ts=1436979735,
        end_ts=1519693374,
        history_list=history,
    )
    _check_for_errors(accountant)
    expected_pnls = PnlTotals()
    check_pnls_and_csv(accountant, expected_pnls)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings, expected', [
    ({'account_for_assets_movements': False, 'taxfree_after_period': -1}, ZERO),
    ({'account_for_assets_movements': True, 'taxfree_after_period': -1}, FVal('-0.0781483014791')),
])
def test_assets_movements_not_accounted_for(accountant, expected):
    # asset_movements_list partially copied from
    # rotkehlchen/tests/integration/test_end_to_end_tax_report.py
    history = [
        Trade(
            timestamp=1446979735,
            location=Location.EXTERNAL,
            base_asset=A_BTC,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=FVal(82),
            rate=FVal('268.678317859'),
            fee=None,
            fee_currency=None,
            link=None,
        ), Trade(
            timestamp=1446979735,
            location=Location.EXTERNAL,
            base_asset=A_ETH,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=FVal(1450),
            rate=FVal('0.2315893'),
            fee=None,
            fee_currency=None,
            link=None,
        ), AssetMovement(
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
        ),
    ]

    accounting_history_process(
        accountant=accountant,
        start_ts=1436979735,
        end_ts=1519693374,
        history_list=history,
    )
    _check_for_errors(accountant)
    expected_pnls = PnlTotals()
    if expected != ZERO:
        expected_pnls[AccountingEventType.ASSET_MOVEMENT] = PNL(taxable=expected, free=ZERO)  # noqa: E501
    check_pnls_and_csv(accountant, expected_pnls)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings, expected', [
    (
        {'calculate_past_cost_basis': False, 'taxfree_after_period': -1},
        PnlTotals({
            AccountingEventType.TRADE: PNL(taxable=FVal('2292.44'), free=ZERO),
            AccountingEventType.FEE: PNL(taxable=FVal('-0.01'), free=ZERO),
        }),
    ),
    (
        {'calculate_past_cost_basis': True, 'taxfree_after_period': -1},
        PnlTotals({
            AccountingEventType.TRADE: PNL(taxable=FVal('1755.083364282'), free=ZERO),
            AccountingEventType.FEE: PNL(taxable=FVal('-0.01'), free=ZERO),
        }),
    ),
])
def test_not_calculate_past_cost_basis(accountant, expected):
    # trades copied from
    # rotkehlchen/tests/integration/test_end_to_end_tax_report.py

    history = [
        Trade(
            timestamp=1446979735,  # 08/11/2015
            location=Location.EXTERNAL,
            base_asset=A_BTC,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=FVal(5),
            rate=FVal('268.678317859'),
            fee=None,
            fee_currency=None,
            link=None,
        ), Trade(
            timestamp=1488373504,  # 29/02/2017
            location=Location.KRAKEN,
            base_asset=A_BTC,
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=FVal(2),
            rate=FVal('1146.22'),
            fee=FVal('0.01'),
            fee_currency=A_EUR,
            link=None,
        ),
    ]
    accounting_history_process(
        accountant=accountant,
        start_ts=1466979735,
        end_ts=1519693374,
        history_list=history,
    )
    check_pnls_and_csv(accountant, expected)


@pytest.mark.parametrize('db_settings', [{
    'taxfree_after_period': -1,
}])
@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_sell_fiat_for_crypto(accountant):
    """
    Test for https://github.com/rotki/rotki/issues/2993
    Make sure that selling fiat for crypto does not give warnings due to
    inability to trace the source of the sold fiat.
    """
    history = [
        Trade(
            timestamp=1446979735,
            location=Location.KRAKEN,
            base_asset=A_EUR,
            quote_asset=A_BTC,
            trade_type=TradeType.SELL,
            amount=FVal(2000),
            rate=FVal('0.002'),
            fee=FVal('0.0012'),
            fee_currency=A_EUR,
            link=None,
        ), Trade(
            # Selling 500 CHF for ETH with 0.004 CHF/ETH. + 0.02 EUR
            # That means 2 ETH for 500 CHF + 0.02 EUR -> with 1.001 CHF/EUR ->
            # (500*1.001 + 0.02)/2 -> 250.26 EUR per ETH
            timestamp=1496979735,
            location=Location.KRAKEN,
            base_asset=A_CHF,
            quote_asset=A_ETH,
            trade_type=TradeType.SELL,
            amount=FVal(500),
            rate=FVal('0.004'),
            fee=FVal('0.02'),
            fee_currency=A_EUR,
            link=None,
        ), Trade(
            timestamp=1506979735,
            location=Location.KRAKEN,
            base_asset=A_ETH,
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=ONE,
            rate=FVal(25000),
            fee=FVal('0.02'),
            fee_currency=A_EUR,
            link=None,
        ),
    ]
    accounting_history_process(
        accountant=accountant,
        start_ts=1436979735,
        end_ts=1519693374,
        history_list=history,
    )
    _check_for_errors(accountant)
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=FVal('24749.74'), free=ZERO),
        AccountingEventType.FEE: PNL(taxable=FVal('-0.0412'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_fees_count_in_cost_basis(accountant):
    """Make sure that asset amounts used in fees are reduced."""
    history = [
        Trade(
            timestamp=1609537953,
            location=Location.KRAKEN,
            base_asset=A_ETH,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=ONE,
            rate=FVal('598.26'),
            fee=ONE,
            fee_currency=A_EUR,
            link=None,
        ), Trade(
            # PNL: 0.5 * 1862.06 - 0.5 * 599.26 -> 631.4
            # fee: -0.5 * 1862.06 + 0.5 * 1862.06 - 0.5 * 599.26 -> -299.63
            timestamp=1624395186,
            location=Location.KRAKEN,
            base_asset=A_ETH,
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=FVal('0.5'),
            rate=FVal('1862.06'),
            fee=FVal('0.5'),
            fee_currency=A_ETH,
            link=None,
        ), Trade(
            timestamp=1625001464,
            location=Location.KRAKEN,
            base_asset=A_ETH,
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=FVal('0.5'),
            rate=FVal('1837.31'),
            fee=None,
            fee_currency=None,
            link=None,
        ),
    ]
    accounting_history_process(
        accountant=accountant,
        start_ts=1436979735,
        end_ts=1625001466,
        history_list=history,
    )

    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=FVal('1550.055'), free=ZERO),
        AccountingEventType.FEE: PNL(taxable=FVal('-300.630'), free=ZERO),
    })
    assert accountant.pots[0].cost_basis.get_calculated_asset_amount(A_ETH) is None
    error = (
        f'No documented acquisition found for ETH(Ethereum) before '
        f'{timestamp_to_date(1625001464, treat_as_local=True)}. '
        f'Let rotki know how you acquired it via a ledger action'
    )
    warnings = accountant.msg_aggregator.consume_warnings()
    assert len(warnings) == 0
    errors = accountant.msg_aggregator.consume_errors()
    assert errors == [error]
    check_pnls_and_csv(accountant, expected_pnls)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_fees_in_received_asset(accountant):
    """
    Test the sell trade where the fee is nominated in the asset received. We had a bug
    where the PnL report said that there was no documented acquisition.
    """
    history = [
        LedgerAction(
            identifier=0,
            timestamp=Timestamp(1539713238),  # 178.615 EUR/ETH
            action_type=LedgerActionType.INCOME,
            location=Location.BINANCE,
            amount=ONE,
            asset=A_ETH,
            rate=None,
            rate_asset=None,
            link=None,
            notes='',
        ),
        Trade(
            # Sell 0.02 ETH for USDT with rate 1000 USDT/ETH and 0.10 USDT fee
            # So acquired 20 USDT for 0.02 ETH + 0.10 USDT
            # So acquired 20 USDT for 0.02 * 598.26 + 0.10 * 0.89 -> 12.0542 EUR
            # So paid 12.0542/20 -> 0.60271 EUR/USDT
            timestamp=1609537953,  # 0.89 EUR/USDT
            location=Location.BINANCE,
            base_asset=A_ETH,  # 598.26 EUR/ETH
            quote_asset=A_USDT,
            trade_type=TradeType.SELL,
            amount=FVal('0.02'),
            rate=FVal(1000),
            fee=FVal('0.10'),
            fee_currency=A_USDT,
            link=None,
        ),
    ]

    accounting_history_process(
        accountant,
        start_ts=1539713238,
        end_ts=1624395187,
        history_list=history,
    )
    _check_for_errors(accountant)
    assert accountant.pots[0].cost_basis.get_calculated_asset_amount(A_USDT.identifier).is_close('19.90')  # noqa: E501
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=ZERO, free=FVal('14.2277')),
        AccountingEventType.FEE: PNL(taxable=FVal('-0.060271'), free=ZERO),
        AccountingEventType.LEDGER_ACTION: PNL(taxable=FVal('178.615'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('dont_mock_price_for', [[A_KFEE]])
def test_kfee_price_in_accounting(accountant):
    """
    Test that KFEEs are correctly handled during accounting

    KFEE price is fixed at $0.01
    """
    history = [
        LedgerAction(
            identifier=0,
            timestamp=Timestamp(1539713238),  # 178.615 EUR/ETH
            action_type=LedgerActionType.INCOME,
            location=Location.KRAKEN,
            amount=FVal(1),
            asset=A_ETH,
            rate=None,
            rate_asset=None,
            link=None,
            notes='',
        ), LedgerAction(
            identifier=0,
            timestamp=Timestamp(1539713238),  # 0.8612 USD/EUR. 1 KFEE = $0.01 so 8.612 EUR
            action_type=LedgerActionType.INCOME,
            location=Location.KRAKEN,
            amount=FVal(1000),
            asset=A_KFEE,
            rate=None,
            rate_asset=None,
            link=None,
            notes='',
        ), Trade(
            timestamp=1609537953,
            location=Location.KRAKEN,  # 0.89 USDT/EUR -> PNL: 20 * 0.89 - 0.02*178.615 ->  14.2277
            base_asset=A_ETH,
            quote_asset=A_USDT,
            trade_type=TradeType.SELL,
            amount=FVal('0.02'),
            rate=FVal(1000),
            fee=FVal(30),  # 0.82411 USD/EUR -> 30 * 0.01 * 0.82411 -> 0.247233
            fee_currency=A_KFEE,  # - 0.247233 + 0.247233 - 30 * 0.01 * 0.8612 -> -0.25836
            link=None,
        ),
    ]
    accounting_history_process(
        accountant,
        start_ts=1539713238,
        end_ts=1624395187,
        history_list=history,
    )
    _check_for_errors(accountant)
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=ZERO, free=FVal('14.2277')),
        AccountingEventType.FEE: PNL(taxable=ZERO, free=FVal('-0.25836')),
        AccountingEventType.LEDGER_ACTION: PNL(taxable=FVal('187.227'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_kraken_staking_events(accountant):
    """
    Test that staking events from kraken are correctly processed
    """
    history = [
        HistoryBaseEntry(
            event_identifier='XXX',
            sequence_index=0,
            timestamp=1640493374000,
            location=Location.KRAKEN,
            location_label='Kraken 1',
            asset=A_ETH2,
            balance=Balance(
                amount=FVal(0.0000541090),
                usd_value=FVal(0.212353475950),
            ),
            notes=None,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
        ), HistoryBaseEntry(
            event_identifier='YYY',
            sequence_index=0,
            timestamp=1636638550000,
            location=Location.KRAKEN,
            location_label='Kraken 1',
            asset=A_ETH2,
            balance=Balance(
                amount=FVal(0.0000541090),
                usd_value=FVal(0.212353475950),
            ),
            notes=None,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
        )]
    _, events = accounting_history_process(
        accountant,
        start_ts=1636638549,
        end_ts=1640493376,
        history_list=history,
    )
    _check_for_errors(accountant)
    expected_pnls = PnlTotals({
        AccountingEventType.STAKING: PNL(taxable=FVal('0.471505826'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls)
    assert len(events) == 2
    expected_pnls = [FVal('0.25114638241'), FVal('0.22035944359')]
    for idx, event in enumerate(events):
        assert event.pnl.taxable == expected_pnls[idx]
        assert event.type == AccountingEventType.STAKING
