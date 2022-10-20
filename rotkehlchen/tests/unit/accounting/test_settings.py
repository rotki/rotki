import pytest

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import (
    ActionType,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.accounting import (
    accounting_history_process,
    check_pnls_and_csv,
    history1,
)
from rotkehlchen.tests.utils.constants import A_DASH
from rotkehlchen.tests.utils.history import prices
from rotkehlchen.tests.utils.messages import no_message_errors
from rotkehlchen.types import (
    AssetAmount,
    AssetMovementCategory,
    Fee,
    Location,
    Price,
    Timestamp,
    TradeType,
)

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
def test_nocrypto2crypto(accountant, google_service):
    accounting_history_process(accountant, 1436979735, 1519693374, history5)
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=ZERO, free=FVal('264693.433642820')),
        AccountingEventType.FEE: PNL(taxable=FVal('-1.172677782721563021308995038'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings', [{
    'taxfree_after_period': -1,
}])
def test_no_taxfree_period(accountant, google_service):
    accounting_history_process(accountant, 1436979735, 1519693374, history5)
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=FVal('265253.1283582327833875'), free=ZERO),
        AccountingEventType.FEE: PNL(taxable=FVal('-0.238868129979988140934107'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings', [{
    'taxfree_after_period': 86400,
}])
def test_big_taxfree_period(accountant, google_service):
    accounting_history_process(accountant, 1436979735, 1519693374, history5)
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=ZERO, free=FVal('265253.1283582327833875')),
        AccountingEventType.FEE: PNL(
            taxable=FVal('-1.172677782721563021308995038'),
            free=FVal('0.9338096527415748803748880375'),
        ),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('ignored_assets', [[A_DASH]])
@pytest.mark.parametrize('db_settings', [{'include_gas_costs': True}, {'include_gas_costs': False}])  # noqa: E501
def test_include_gas_costs(accountant, google_service):
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
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(tx_hash),
            sequence_index=0,
            timestamp=1569924574000,
            location=Location.BLOCKCHAIN,
            location_label=addr1,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.000030921')),
            notes='Burned 0.000030921 ETH for gas',
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            counterparty=CPT_GAS,
        )]
    accounting_history_process(accountant, start_ts=1436979735, end_ts=1619693374, history_list=history)  # noqa: E501
    no_message_errors(accountant.msg_aggregator)
    expected = ZERO
    expected_pnls = PnlTotals()
    if accountant.pots[0].settings.include_gas_costs:
        expected = FVal('-0.0052163727')
        expected_pnls[AccountingEventType.TRANSACTION_EVENT] = PNL(taxable=expected, free=ZERO)
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('ignored_assets', [[A_DASH]])
def test_ignored_transactions(accountant, google_service):
    addr1 = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'
    tx_hash = '0x5cc0e6e62753551313412492296d5e57bea0a9d1ce507cc96aa4aa076c5bde7a'
    ignored_tx_hash = '0x1000e6e62753551313412492296d5e57bea0a9d1ce507cc96aa4aa076c5bde11'
    with accountant.db.user_write() as cursor:
        accountant.db.add_to_ignored_action_ids(
            write_cursor=cursor,
            action_type=ActionType.ETHEREUM_TRANSACTION,
            identifiers=[ignored_tx_hash],
        )
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
            identifier='uniqueid1',  # should normally be given by DB at write time
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(tx_hash),
            sequence_index=0,
            timestamp=1569924574000,
            location=Location.BLOCKCHAIN,
            location_label=addr1,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.000030921')),
            notes='Burned 0.000030921 ETH for gas',
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            identifier='uniqueid2',    # should normally be given by DB at write time
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(ignored_tx_hash),
            sequence_index=0,
            timestamp=1569934574000,
            location=Location.BLOCKCHAIN,
            location_label=addr1,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.000040921')),
            notes='Burned 0.000040921 ETH for gas',
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            counterparty=CPT_GAS,
        )]
    _, events = accounting_history_process(accountant, start_ts=1436979735, end_ts=1619693374, history_list=history)  # noqa: E501
    assert len(events) == 3
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({
        AccountingEventType.TRANSACTION_EVENT: PNL(taxable=FVal('-0.0052163727'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('ignored_assets', [[A_DASH]])
def test_ignored_assets(accountant, google_service):
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
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=FVal('559.6947154127833875'), free=ZERO),
        AccountingEventType.FEE: PNL(taxable=FVal('-0.238868129979988140934107'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_margin_events_affect_gained_lost_amount(accountant, google_service):
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
            amount=ONE,
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
    no_message_errors(accountant.msg_aggregator)
    assert accountant.pots[0].cost_basis.get_calculated_asset_amount('BTC').is_close('3.7468')
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=FVal('1940.9761588'), free=ZERO),
        AccountingEventType.FEE: PNL(taxable=FVal('-1.87166029184'), free=ZERO),
        AccountingEventType.MARGIN_POSITION: PNL(taxable=FVal('-44.47442060'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings, expected', [
    ({'account_for_assets_movements': False, 'taxfree_after_period': -1}, ZERO),
    ({'account_for_assets_movements': True, 'taxfree_after_period': -1}, FVal('-0.0781483014791')),
])
def test_assets_movements_not_accounted_for(accountant, expected, google_service):
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
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals()
    if expected != ZERO:
        expected_pnls[AccountingEventType.ASSET_MOVEMENT] = PNL(taxable=expected, free=ZERO)  # noqa: E501
    check_pnls_and_csv(accountant, expected_pnls, google_service)


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
def test_not_calculate_past_cost_basis(accountant, expected, google_service):
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
    check_pnls_and_csv(accountant, expected, google_service)
