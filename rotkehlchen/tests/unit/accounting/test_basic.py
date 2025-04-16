from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.accounting.types import MissingPrice
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.modules.eth2.structures import ValidatorDailyStats
from rotkehlchen.chain.evm.decoding.cowswap.constants import CPT_COWSWAP
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_BTC, A_COMP, A_ETH, A_EUR, A_USD, A_USDC, A_WBTC
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.tests.utils.accounting import (
    accounting_history_process,
    check_pnls_and_csv,
    history1,
)
from rotkehlchen.tests.utils.constants import A_CHF, A_XMR
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.tests.utils.history import prices
from rotkehlchen.tests.utils.messages import no_message_errors
from rotkehlchen.types import (
    EVM_CHAINS_WITH_TRANSACTIONS,
    CostBasisMethod,
    Location,
    Price,
    Timestamp,
    TimestampMS,
    TradeType,
)

if TYPE_CHECKING:
    from rotkehlchen.accounting.accountant import Accountant


@pytest.mark.parametrize(('db_settings', 'expected_pnls'), [
    (
        {'cost_basis_method': CostBasisMethod.FIFO},
        PnlTotals({
            AccountingEventType.TRADE: PNL(taxable=FVal('559.7007917527833875'), free=ZERO),
            AccountingEventType.FEE: PNL(taxable=ZERO, free=ZERO),
        }),
    ),
    (
        {'cost_basis_method': CostBasisMethod.ACB},
        PnlTotals({
            AccountingEventType.TRADE: PNL(taxable=FVal('551.2649524225750541683933333'), free=ZERO),  # noqa: E501
            AccountingEventType.FEE: PNL(taxable=ZERO, free=ZERO),
        }),
    ),
])
@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_simple_accounting(accountant, google_service, expected_pnls):
    accounting_history_process(accountant, 1436979735, 1495751688, history1)
    no_message_errors(accountant.msg_aggregator)
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize(('db_settings', 'expected_pnl_totals'), [
    (
        {'include_fees_in_cost_basis': True},
        PnlTotals({
            AccountingEventType.TRADE: PNL(taxable=FVal('74.24348625705538353047999998'), free=ZERO),  # noqa: E501
            AccountingEventType.FEE: PNL(taxable=ZERO, free=ZERO),
        }),
    ),
    (
        {'include_fees_in_cost_basis': False},
        PnlTotals({
            AccountingEventType.TRADE: PNL(taxable=FVal('74.4107983124540625'), free=ZERO),
            AccountingEventType.FEE: PNL(taxable=FVal('-0.418612202811480978'), free=ZERO),
        }),
    ),
])
def test_selling_crypto_bought_with_crypto(accountant, google_service, expected_pnl_totals):
    history = [
        Trade(
            timestamp=Timestamp(1446979735),
            location=Location.EXTERNAL,
            base_asset=A_BTC,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=FVal(82),
            rate=Price(FVal('268.678317859')),
            fee=None,
            fee_currency=None,
            link=None,
        ), Trade(
            timestamp=Timestamp(1449809536),  # cryptocompare hourly BTC/EUR price: 386.175
            location=Location.POLONIEX,
            base_asset=A_XMR,  # cryptocompare hourly XMR/EUR price: 0.39665
            quote_asset=A_BTC,
            trade_type=TradeType.BUY,
            amount=FVal(375),
            rate=Price(FVal('0.0010275')),
            fee=FVal('0.9375'),
            fee_currency=A_XMR,
            link=None,
        ), Trade(
            timestamp=Timestamp(1458070370),  # cryptocompare hourly rate XMR/EUR price: 1.0443027675  # noqa: E501
            location=Location.KRAKEN,
            base_asset=A_XMR,
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=FVal(45),
            rate=Price(FVal('1.0443027675')),
            fee=FVal('0.117484061344'),
            fee_currency=A_XMR,
            link=None,
        ),
    ]
    accounting_history_process(accountant, Timestamp(1436979735), Timestamp(1495751688), history)
    no_message_errors(accountant.msg_aggregator)
    # Make sure buying XMR with BTC also creates a BTC sell
    sells = accountant.pots[0].cost_basis.get_events(A_BTC).spends
    assert len(sells) == 1
    assert sells[0].timestamp == 1449809536
    assert sells[0].amount.is_close(FVal('0.3853125'))
    assert sells[0].rate.is_close(FVal('386.175'))

    check_pnls_and_csv(accountant, expected_pnl_totals, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_buy_event_creation(accountant):
    history = [
        Trade(
            timestamp=Timestamp(1476979735),
            location=Location.KRAKEN,
            base_asset=A_BTC,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=FVal(5),
            rate=Price(FVal('578.505')),
            fee=FVal('0.0012'),
            fee_currency=A_BTC,
            link=None,
        ), Trade(
            timestamp=Timestamp(1476979735),
            location=Location.KRAKEN,
            base_asset=A_BTC,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=FVal(5),
            rate=Price(FVal('578.505')),
            fee=FVal('0.0012'),
            fee_currency=A_EUR,
            link=None,
        ),
    ]
    accounting_history_process(accountant, Timestamp(1436979735), Timestamp(1519693374), history)
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
@pytest.mark.parametrize('db_settings', [{'include_fees_in_cost_basis': False}])
def test_no_corresponding_buy_for_sell(accountant, google_service):
    """Test that if there is no corresponding buy for a sell, the entire sell counts as profit"""
    history = [Trade(
        timestamp=Timestamp(1476979735),
        location=Location.KRAKEN,
        base_asset=A_BTC,
        quote_asset=A_EUR,
        trade_type=TradeType.SELL,
        amount=ONE,
        rate=Price(FVal('2519.62')),
        fee=FVal('0.02'),
        fee_currency=A_EUR,
        link=None,
    )]
    accounting_history_process(
        accountant=accountant,
        start_ts=Timestamp(1436979735),
        end_ts=Timestamp(1519693374),
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
        start_ts=Timestamp(1436979735),
        end_ts=Timestamp(1519693374),
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
            timestamp=Timestamp(1446979735),
            location=Location.KRAKEN,
            base_asset=A_EUR,
            quote_asset=A_BTC,
            trade_type=TradeType.SELL,
            amount=FVal(2000),
            rate=Price(FVal('0.002')),
            fee=FVal('0.0012'),
            fee_currency=A_EUR,
            link=None,
        ), Trade(
            # Selling 500 CHF for ETH with 0.004 CHF/ETH. + 0.02 EUR
            # That means 2 ETH for 500 CHF + 0.02 EUR -> with 1.001 CHF/EUR ->
            # (500*1.001 + 0.02)/2 -> 250.26 EUR per ETH
            timestamp=Timestamp(1496979735),
            location=Location.KRAKEN,
            base_asset=A_CHF,
            quote_asset=A_ETH,
            trade_type=TradeType.SELL,
            amount=FVal(500),
            rate=Price(FVal('0.004')),
            fee=FVal('0.02'),
            fee_currency=A_EUR,
            link=None,
        ), Trade(
            timestamp=Timestamp(1506979735),
            location=Location.KRAKEN,
            base_asset=A_ETH,
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=ONE,
            rate=Price(FVal(25000)),
            fee=FVal('0.02'),
            fee_currency=A_EUR,
            link=None,
        ),
    ]
    accounting_history_process(
        accountant=accountant,
        start_ts=Timestamp(1436979735),
        end_ts=Timestamp(1519693374),
        history_list=history,
    )
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=FVal('24749.72'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('db_settings', [{
    'taxfree_after_period': -1,
}])
@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_direct_profit_currency_fiat_trades(accountant, google_service):
    """Test that buying crypto with fiat and then selling crypto for fiat takes the
    trade rate as is, if it's the chosen profit currency
    """
    buy_price, sell_price = Price(FVal('0.80')), Price(FVal('10.9'))
    history = [
        Trade(
            timestamp=Timestamp(1446979735),  # 1 ETH = 0.8583 EUR according to oracle
            location=Location.KRAKEN,
            base_asset=A_ETH,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=ONE,
            rate=buy_price,  # But we bought in discount
            fee=ZERO,
            fee_currency=A_EUR,
            link=None,
        ), Trade(
            timestamp=Timestamp(1463508234),  # 1 ETH = 10.785 EUR according to oracle
            location=Location.KRAKEN,
            base_asset=A_ETH,
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=ONE,
            rate=sell_price,  # But we sold for more than oracle
            fee=ZERO,
            fee_currency=A_EUR,
            link=None,
        ),
    ]
    accounting_history_process(
        accountant=accountant,
        start_ts=Timestamp(1436979735),
        end_ts=Timestamp(1519693374),
        history_list=history,
    )
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=sell_price - buy_price, free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('db_settings', [{
    'taxfree_after_period': -1,
}])
@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_other_currency_fiat_trades(accountant, google_service):
    """Test that buying crypto with fiat and then selling crypto for fiat takes the
    price from the fiat part.
    """
    buy_price, sell_price = Price(FVal('0.80')), Price(FVal('10.9'))
    history = [
        Trade(
            timestamp=Timestamp(1446979735),  # 1 ETH = 0.8583 EUR according to oracle
            location=Location.KRAKEN,
            base_asset=A_ETH,
            quote_asset=A_USD,
            trade_type=TradeType.BUY,
            amount=ONE,
            rate=buy_price,  # But we bought in discount
            fee=ZERO,
            fee_currency=A_USD,
            link=None,
        ), Trade(
            timestamp=Timestamp(1463508234),  # 1 ETH = 10.785 EUR according to oracle
            location=Location.KRAKEN,
            base_asset=A_ETH,
            quote_asset=A_USD,  # USD/EUR -> 0.8878
            trade_type=TradeType.SELL,
            amount=ONE,
            rate=sell_price,  # But we sold for more than oracle
            fee=ZERO,
            fee_currency=A_USD,
            link=None,
        ),
    ]
    accounting_history_process(
        accountant=accountant,
        start_ts=Timestamp(1436979735),
        end_ts=Timestamp(1519693374),
        history_list=history,
    )
    no_message_errors(accountant.msg_aggregator)
    expected_pnl = sell_price * prices['USD']['EUR'][history[1].timestamp] - buy_price * prices['USD']['EUR'][history[0].timestamp]  # noqa: E501
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=expected_pnl, free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_asset_and_price_not_found_in_history_processing(accountant):
    """
    Make sure that in history processing if no price is found for a trade it's added to a
    `missing_prices` list and no error is logged.

    Regression for https://github.com/rotki/rotki/issues/432
    Updated with https://github.com/rotki/rotki/pull/4196
    """
    PriceHistorian().set_oracles_order([HistoricalPriceOracle.CRYPTOCOMPARE])  # enforce single oracle for VCR  # noqa: E501
    fgp = EvmToken('eip155:1/erc20:0xd9A8cfe21C232D485065cb62a96866799d4645f7')
    time = Timestamp(1492685761)
    trade = Trade(
        timestamp=time,
        location=Location.KRAKEN,
        base_asset=A_EUR,
        quote_asset=A_BTC,
        trade_type=TradeType.BUY,
        amount=FVal('2.5'),
        rate=Price(FVal(.11000)),
        fee=FVal('0.15'),
        fee_currency=fgp,
        link=None,
    )
    history = [trade, trade]  # duplicate missing price
    accounting_history_process(
        accountant,
        start_ts=Timestamp(0),
        end_ts=Timestamp(1514764799),  # 31/12/2017
        history_list=history,
    )
    errors = accountant.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(accountant.pots[0].cost_basis.missing_prices) == 1
    assert next(iter(accountant.pots[0].cost_basis.missing_prices)) == MissingPrice(
        from_asset=fgp,
        to_asset=A_EUR,
        time=time,
        rate_limited=False,
    )


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('force_no_price_found_for', [[(A_COMP, 1446979735)]])
def test_acquisition_price_not_found(accountant, google_service):
    """Test that if for an acquisition the price is not found, price of
    zero is taken and asset is not ignored and no missing acquisition is counted"""
    history = [
        HistoryEvent(
            event_identifier='1',
            sequence_index=0,
            timestamp=TimestampMS(1446979735000),
            location=Location.EXTERNAL,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_COMP,
            amount=ONE,
        ), Trade(
            timestamp=Timestamp(1635314397),  # cryptocompare hourly COMP/EUR price: 261.39
            location=Location.POLONIEX,
            base_asset=A_COMP,
            quote_asset=A_EUR,
            trade_type=TradeType.SELL,
            amount=ONE,
            rate=Price(FVal('261.39')),
            link=None,
        ),
    ]
    accounting_history_process(accountant, Timestamp(1436979735), Timestamp(1636314397), history)
    no_message_errors(accountant.msg_aggregator)
    comp_acquisitions = accountant.pots[0].cost_basis.get_events(A_COMP).used_acquisitions
    assert len(comp_acquisitions) == 1
    expected_pnls = PnlTotals({
        AccountingEventType.TRANSACTION_EVENT: PNL(taxable=ZERO, free=ZERO),
        AccountingEventType.TRADE: PNL(taxable=ZERO, free=FVal('261.39')),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_no_fiat_missing_acquisitions(accountant):
    history = [
        Trade(
            timestamp=Timestamp(1459024920),
            location=Location.UPHOLD,
            base_asset=A_EUR,
            quote_asset=A_USD,
            trade_type=TradeType.BUY,
            amount=ONE,
            rate=Price(FVal('0.8982')),
            link=None,
        ),
        Trade(
            timestamp=Timestamp(1446979735),
            location=Location.POLONIEX,
            base_asset=A_BTC,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=ONE,
            rate=Price(FVal(355.9)),
            link=None,
        ),
    ]
    accounting_history_process(accountant, Timestamp(1446979735), Timestamp(1635314397), history)
    no_message_errors(accountant.msg_aggregator)
    missing_acquisitions = accountant.pots[0].cost_basis.missing_acquisitions
    assert missing_acquisitions == []


def test_all_chains_have_explorers(accountant: 'Accountant'):
    """Test that all chain in the csv exporter have a valid explorer url"""
    for chain in EVM_CHAINS_WITH_TRANSACTIONS:
        assert chain in accountant.csvexporter.transaction_explorers


@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_non_history_event_in_history_iterator(accountant):
    """Test that the PnL report does not fail if a non-history event follows a swap

    Regression test for: https://github.com/rotki/rotki/issues/7009
    """
    tx_hash = make_evm_tx_hash()
    user_address = make_evm_address()
    contract_address = make_evm_address()
    swap_amount_str = '0.99'
    receive_amount_str = '10000'
    event_timestamp_ms = TimestampMS(1635314397 - DAY_IN_SECONDS * 1000)
    history = [HistoryEvent(
        event_identifier='1',
        sequence_index=0,
        timestamp=event_timestamp_ms,
        location=Location.EXTERNAL,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_WBTC,
        amount=ONE,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=event_timestamp_ms,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_WBTC,
        amount=FVal(swap_amount_str),
        location_label=user_address,
        notes=f'Swap {swap_amount_str} WBTC in cowswap',
        counterparty=CPT_COWSWAP,
        address=contract_address,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=event_timestamp_ms,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDC,
        amount=FVal(receive_amount_str),
        location_label=user_address,
        notes=f'Receive {receive_amount_str} USDC as the result of a swap in cowswap',
        counterparty=CPT_COWSWAP,
        address=contract_address,
    ), ValidatorDailyStats(
        validator_index=1,
        timestamp=Timestamp(1635314397 - DAY_IN_SECONDS + 1),
        pnl=FVal('0.1'),
    )]
    accounting_history_process(accountant, Timestamp(0), Timestamp(1635314397), history)
    no_message_errors(accountant.msg_aggregator)
    missing_acquisitions = accountant.pots[0].cost_basis.missing_acquisitions
    assert missing_acquisitions == []
