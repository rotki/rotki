from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH, A_ETH2, A_EUR, A_KFEE, A_USD, A_USDT
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.history.events.structures.swap import create_swap_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.accounting import (
    accounting_create_and_process_history,
    accounting_history_process,
    check_pnls_and_csv,
    get_calculated_asset_amount,
)
from rotkehlchen.tests.utils.constants import A_GBP
from rotkehlchen.tests.utils.history import prices
from rotkehlchen.tests.utils.messages import no_message_errors
from rotkehlchen.types import AssetAmount, Location, Price, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_ms_to_sec

if TYPE_CHECKING:
    from rotkehlchen.accounting.accountant import Accountant
    from rotkehlchen.api.server import APIServer


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('dont_mock_price_for', [[A_KFEE]])
def test_kfee_price_in_accounting(accountant, google_service):
    """
    Test that KFEEs are correctly handled during accounting

    KFEE price is fixed at $0.01
    """
    history = [
        HistoryEvent(
            event_identifier='1',
            sequence_index=0,
            timestamp=TimestampMS(1539713238000),  # 178.615 EUR/ETH
            location=Location.COINBASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ONE,
        ), HistoryEvent(
            event_identifier='2',
            sequence_index=0,
            timestamp=TimestampMS(1539713238000),  # 0.8612 USD/EUR. 1 KFEE = $0.01 so 8.612 EUR
            location=Location.COINBASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_KFEE,
            amount=FVal(1000),
        ), *create_swap_events(
            timestamp=TimestampMS(1609537953000),  # PNL: 598.26 ETH/EUR -> PNL: 0.02 * 598.26 - 0.02*178.615 ->  8.3929  # noqa: E501
            location=Location.KRAKEN,
            event_identifier='1xyz',
            spend=AssetAmount(asset=A_ETH, amount=FVal('0.02')),
            receive=AssetAmount(asset=A_USDT, amount=FVal('0.02') * FVal(1000)),
            fee=AssetAmount(asset=A_KFEE, amount=FVal(30)),  # KFEE is not taken into account
        ),
    ]
    accounting_history_process(
        accountant,
        start_ts=Timestamp(1539713238),
        end_ts=Timestamp(1624395187),
        history_list=history,
    )
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=ZERO, free=FVal('8.3929')),
        AccountingEventType.TRANSACTION_EVENT: PNL(taxable=FVal('187.227'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_fees_count_in_cost_basis(accountant, google_service):
    """Make sure that asset amounts used in fees are reduced."""
    history = [*create_swap_events(
        timestamp=TimestampMS(1609537953000),
        location=Location.KRAKEN,
        event_identifier='1xyz',
        spend=AssetAmount(asset=A_EUR, amount=ONE * FVal('598.26')),
        receive=AssetAmount(asset=A_ETH, amount=ONE),
        fee=AssetAmount(asset=A_EUR, amount=ONE),
    ),
    # fee: 0.5 * 1862.06 -> 931.03
    # PNL: 0.5 * 1862.06 - 0.5 * 599.26 - fee -> -299.63
    *create_swap_events(
        timestamp=TimestampMS(1624395186000),
        location=Location.KRAKEN,
        event_identifier='2xyz',
        spend=AssetAmount(asset=A_ETH, amount=FVal('0.5')),
        receive=AssetAmount(asset=A_EUR, amount=FVal('0.5') * FVal('1862.06')),
        fee=AssetAmount(asset=A_ETH, amount=FVal('0.5')),
    ),
    # No ETH is owned at this point.
    # PNL: 0.5 * 1837.31 -> 918.655
    *create_swap_events(
        timestamp=TimestampMS(1625001464000),
        location=Location.KRAKEN,
        event_identifier='3xyz',
        spend=AssetAmount(asset=A_ETH, amount=FVal('0.5')),
        receive=AssetAmount(asset=A_EUR, amount=FVal('0.5') * FVal('1837.31')),
    )]
    accounting_history_process(
        accountant=accountant,
        start_ts=Timestamp(1436979735),
        end_ts=Timestamp(1625001466),
        history_list=history,
    )

    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=FVal('619.025'), free=ZERO),
    })
    assert get_calculated_asset_amount(accountant.pots[0].cost_basis, A_ETH) is None
    warnings = accountant.msg_aggregator.consume_warnings()
    assert len(warnings) == 0
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings', [{'include_fees_in_cost_basis': False}])
def test_fees_in_received_asset(accountant, google_service):
    """
    Test the sell trade where the fee is nominated in the asset received. We had a bug
    where the PnL report said that there was no documented acquisition.
    """
    history = [
        HistoryEvent(
            event_identifier='1',
            sequence_index=0,
            timestamp=TimestampMS(1539713238000),  # 178.615 EUR/ETH
            location=Location.BINANCE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ONE,
        ),
        # Sell 0.02 ETH for USDT with rate 1000 USDT/ETH and 0.10 USDT fee
        # So acquired 20 USDT for 0.02 ETH + 0.10 USDT
        # So acquired 20 USDT for 0.02 * 598.26 + 0.10 * 0.89 -> 12.0542 EUR
        # So paid 12.0542/20 -> 0.60271 EUR/USDT
        *create_swap_events(
            timestamp=TimestampMS(1609537953000),  # 0.89 EUR/USDT
            location=Location.BINANCE,
            event_identifier='1xyz',
            spend=AssetAmount(asset=A_ETH, amount=FVal('0.02')),  # 598.26 EUR/ETH
            receive=AssetAmount(asset=A_USDT, amount=FVal('0.02') * FVal(1000)),  # PNL: 598.26 ETH/EUR -> PNL: 0.02 * 598.26 - 0.02*178.615 ->  8.3929  # noqa: E501
            fee=AssetAmount(amount=FVal('0.10'), asset=A_USDT),
        ),
    ]

    accounting_history_process(
        accountant,
        start_ts=Timestamp(1539713238),
        end_ts=Timestamp(1624395187),
        history_list=history,
    )
    no_message_errors(accountant.msg_aggregator)
    assert get_calculated_asset_amount(accountant.pots[0].cost_basis, A_USDT).is_close('19.90')
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=ZERO, free=FVal('8.3929')),
        AccountingEventType.FEE: PNL(taxable=FVal('-0.059826'), free=ZERO),
        AccountingEventType.TRANSACTION_EVENT: PNL(taxable=FVal('178.615'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [{
    'ETH': {'GBP': {1609537953: FVal('534.94')}},
    'USD': {'GBP': {1609537953: FVal('0.741076')}},
}])
@pytest.mark.parametrize('should_mock_price_queries', [True])
def test_main_currency_is_respected(
        accountant: 'Accountant',
        mocked_price_queries: dict[str, dict[str, dict[int, FVal]]],
) -> None:
    """Verify that the price after processing trades respects the main currency. We change the
    main currency to GBP and assert the price for a trade using a different currency as quote.
    """
    with accountant.db.conn.write_ctx() as cursor:
        accountant.db.set_setting(cursor, name='main_currency', value=A_GBP)

    trade_rate = Price(FVal('2403.20'))
    history = create_swap_events(
        timestamp=TimestampMS(1609537953000),
        location=Location.EXTERNAL,
        event_identifier='1xyz',
        spend=AssetAmount(asset=A_ETH2, amount=FVal('0.04')),
        receive=AssetAmount(asset=A_USD, amount=FVal('0.04') * trade_rate),
        fee=AssetAmount(asset=A_EUR, amount=ZERO),
    )
    accounting_history_process(
        accountant=accountant,
        start_ts=Timestamp(1436979735),
        end_ts=Timestamp(1625001466),
        history_list=history,
    )
    errors = accountant.msg_aggregator.consume_errors()
    warnings = accountant.msg_aggregator.consume_warnings()
    assert len(warnings) == len(errors) == 0
    # Check that the price is correctly computed in GBP
    assert accountant.pots[0].processed_events[0].price == trade_rate * mocked_price_queries['USD']['GBP'][1609537953]  # noqa: E501


@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('ethereum_accounts', [[]])
@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('initialize_accounting_rules', [True])
def test_process_events_with_duplicate_timestamps(
        rotkehlchen_api_server: 'APIServer',
) -> None:
    """Verify that events with the same timestamp are properly processed.
    Regression test for https://github.com/orgs/rotki/projects/11?pane=issue&itemId=115660014
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    history: list[HistoryBaseEntry] = [AssetMovement(
        timestamp=TimestampMS(1500000000000),
        location=Location.KRAKEN,
        event_type=HistoryEventType.DEPOSIT,
        asset=A_EUR,
        amount=FVal('100'),
    )]
    history.extend(create_swap_events(
        timestamp=TimestampMS(1624791600000),
        location=Location.KRAKEN,
        event_identifier='1xyz',
        spend=AssetAmount(asset=A_EUR, amount=FVal('50')),
        receive=AssetAmount(asset=A_ETH, amount=FVal('0.04')),
    ))
    history.extend(create_swap_events(
        timestamp=TimestampMS(1624791600000),
        location=Location.KRAKEN,
        event_identifier='2xyz',
        spend=AssetAmount(asset=A_EUR, amount=FVal('50')),
        receive=AssetAmount(asset=A_ETH, amount=FVal('0.04')),
    ))
    with rotki.data.db.conn.write_ctx() as write_cursor:
        DBHistoryEvents(rotki.data.db).add_history_events(
            write_cursor=write_cursor,
            history=history,
        )
        # Also add a non-HistoryBaseEntry event to confirm it's also properly handled.
        rotki.data.db.add_margin_positions(
            write_cursor=write_cursor,
            margin_positions=[MarginPosition(
                location=Location.KRAKEN,
                open_time=Timestamp(1607900400),
                close_time=Timestamp(1624791600),
                profit_loss=FVal('0.5'),
                pl_currency=A_ETH,
                fee=ZERO,
                fee_currency=A_EUR,
                link='',
            )],
        )

    _, events = accounting_create_and_process_history(
        rotki=rotki,
        start_ts=Timestamp(0),
        end_ts=Timestamp(1624791600),
    )
    assert len(events) == 5  # margin position and the spend/receive from both swaps
    assert events[0].event_type == AccountingEventType.MARGIN_POSITION
    for i in range(1, 5):
        assert events[i].event_type == AccountingEventType.TRADE


@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('ethereum_accounts', [[]])
@pytest.mark.parametrize('initialize_accounting_rules', [True])
def test_fiat_income_taxable_pnl(
        rotkehlchen_api_server: 'APIServer',
) -> None:
    """Check that fiat IN events are properly counted as taxable income.
    Regression test for https://github.com/rotki/rotki/issues/10419
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with rotki.data.db.conn.write_ctx() as write_cursor:
        DBHistoryEvents(rotki.data.db).add_history_events(
            write_cursor=write_cursor,
            history=[HistoryEvent(
                event_identifier='event1',
                sequence_index=0,
                timestamp=(event_ts_ms := TimestampMS(1500000000000)),
                location=Location.EXTERNAL,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_EUR,
                amount=(event_amount := FVal('100')),
            )],
        )

    expected_event = ProcessedAccountingEvent(
        event_type=AccountingEventType.TRANSACTION_EVENT,
        notes='',
        location=Location.EXTERNAL,
        timestamp=(event_ts := ts_ms_to_sec(event_ts_ms)),
        asset=A_EUR,
        free_amount=ZERO,
        taxable_amount=event_amount,
        price=Price(ONE),
        pnl=PNL(taxable=event_amount, free=ZERO),
        cost_basis=None,
        index=0,
    )
    expected_event.count_cost_basis_pnl = True
    _, events = accounting_create_and_process_history(
        rotki=rotki,
        start_ts=Timestamp(0),
        end_ts=Timestamp(event_ts + 1),
    )
    assert events == [expected_event]
