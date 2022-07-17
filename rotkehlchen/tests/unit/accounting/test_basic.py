import pytest

from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.accounting.types import MissingPrice
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_BTC, A_COMP, A_ETH, A_EUR, A_USD
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.accounting import (
    accounting_history_process,
    check_pnls_and_csv,
    history1,
)
from rotkehlchen.tests.utils.constants import A_CHF, A_XMR
from rotkehlchen.tests.utils.history import prices
from rotkehlchen.tests.utils.messages import no_message_errors
from rotkehlchen.types import Location, Timestamp, TradeType


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_simple_accounting(accountant, google_service):
    accounting_history_process(accountant, 1436979735, 1495751688, history1)
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=FVal('559.6947154'), free=ZERO),
        AccountingEventType.FEE: PNL(taxable=FVal('-0.23886813'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_selling_crypto_bought_with_crypto(accountant, google_service):
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
    no_message_errors(accountant.msg_aggregator)
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
    check_pnls_and_csv(accountant, expected_pnls, google_service)


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
    no_message_errors(accountant.msg_aggregator)
    buys = accountant.pots[0].cost_basis.get_events(A_BTC).acquisitions_manager.get_acquisitions()
    assert len(buys) == 2
    assert buys[0].amount == FVal(5)
    assert buys[0].timestamp == 1476979735
    assert buys[0].rate.is_close('578.6438412')  # (578.505 * 5 + 0.0012 * 578.505)/5

    assert buys[1].amount == FVal(5)
    assert buys[1].timestamp == 1476979735
    assert buys[1].rate == FVal('578.50524')  # (578.505 * 5 + 0.0012)/5


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_no_corresponding_buy_for_sell(accountant, google_service):
    """Test that if there is no corresponding buy for a sell, the entire sell counts as profit"""
    history = [Trade(
        timestamp=1476979735,
        location=Location.KRAKEN,
        base_asset=A_BTC,
        quote_asset=A_EUR,
        trade_type=TradeType.SELL,
        amount=ONE,
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
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_accounting_works_for_empty_history(accountant, google_service):
    history = []
    accounting_history_process(
        accountant=accountant,
        start_ts=1436979735,
        end_ts=1519693374,
        history_list=history,
    )
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals()
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('db_settings', [{
    'taxfree_after_period': -1,
}])
@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_sell_fiat_for_crypto(accountant, google_service):
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
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=FVal('24749.74'), free=ZERO),
        AccountingEventType.FEE: PNL(taxable=FVal('-0.0412'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_asset_and_price_not_found_in_history_processing(accountant):
    """
    Make sure that in history processing if no price is found for a trade it's added to a
    `missing_prices` list and no error is logged.

    Regression for https://github.com/rotki/rotki/issues/432
    Updated with https://github.com/rotki/rotki/pull/4196
    """
    fgp = EvmToken('eip155:1/erc20:0xd9A8cfe21C232D485065cb62a96866799d4645f7')
    time = Timestamp(1492685761)
    trade = Trade(
        timestamp=time,
        location=Location.KRAKEN,
        base_asset=fgp,
        quote_asset=A_BTC,
        trade_type=TradeType.BUY,
        amount=FVal('2.5'),
        rate=FVal(.11000),
        fee=FVal('0.15'),
        fee_currency=fgp,
        link=None,
    )
    history = [trade, trade]  # duplicate missing price
    accounting_history_process(
        accountant,
        start_ts=0,
        end_ts=1514764799,  # 31/12/2017
        history_list=history,
    )
    errors = accountant.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(accountant.pots[0].cost_basis.missing_prices) == 1
    assert list(accountant.pots[0].cost_basis.missing_prices)[0] == MissingPrice(
        from_asset=fgp,
        to_asset=A_EUR,
        time=time,
    )


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('force_no_price_found_for', [[(A_COMP, 1446979735)]])
def test_acquisition_price_not_found(accountant, google_service):
    """Test that if for an acquisition the price is not found, price of
    zero is taken and asset is not ignored and no missing acquisition is counted"""
    history = [
        LedgerAction(
            identifier=1,
            timestamp=1446979735,
            action_type=LedgerActionType.INCOME,
            location=Location.EXTERNAL,
            asset=A_COMP,
            amount=ONE,
        ), Trade(
            timestamp=1635314397,  # cryptocompare hourly COMP/EUR price: 261.39
            location=Location.POLONIEX,
            base_asset=A_COMP,
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=ONE,
            rate=FVal('261.39'),
            link=None,
        ),
    ]
    accounting_history_process(accountant, 1436979735, 1636314397, history)
    no_message_errors(accountant.msg_aggregator)
    comp_acquisitions = accountant.pots[0].cost_basis.get_events(A_COMP).used_acquisitions
    assert len(comp_acquisitions) == 1
    expected_pnls = PnlTotals({
        AccountingEventType.LEDGER_ACTION: PNL(taxable=ZERO, free=ZERO),
        AccountingEventType.TRADE: PNL(taxable=ZERO, free=FVal('261.39')),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_no_fiat_missing_acquisitions(accountant):
    history = [
        Trade(
            timestamp=1459024920,
            location=Location.UPHOLD,
            base_asset=A_EUR,
            quote_asset=A_USD,
            trade_type=TradeType.BUY,
            amount=ONE,
            rate=FVal('0.8982'),
            link=None,
        ),
        Trade(
            timestamp=1446979735,
            location=Location.POLONIEX,
            base_asset=A_BTC,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=ONE,
            rate=FVal(355.9),
            link=None,
        ),
    ]
    accounting_history_process(accountant, 1446979735, 1635314397, history)
    no_message_errors(accountant.msg_aggregator)
    missing_acquisitions = accountant.pots[0].cost_basis.missing_acquisitions
    assert missing_acquisitions == []
