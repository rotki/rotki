import os

import pytest

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR
from rotkehlchen.db.accounting_rules import DBAccountingRules
from rotkehlchen.exchanges.data_structures import MarginPosition, Trade
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.eth2 import EthWithdrawalEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.accounting import (
    accounting_history_process,
    assert_pnl_totals_close,
    check_pnls_and_csv,
    get_calculated_asset_amount,
    history1,
)
from rotkehlchen.tests.utils.constants import A_DASH
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.history import prices
from rotkehlchen.tests.utils.messages import no_message_errors
from rotkehlchen.types import (
    Location,
    Price,
    Timestamp,
    TimestampMS,
    TradeType,
    deserialize_evm_tx_hash,
)

history5 = history1 + [Trade(
    timestamp=Timestamp(1512693374),  # cryptocompare hourly BTC/EUR price: 537.805
    location=Location.KRAKEN,
    base_asset=A_BTC,
    quote_asset=A_EUR,
    trade_type=TradeType.SELL,
    amount=FVal('20'),
    rate=Price(FVal('13503.35')),
    fee=None,
    fee_currency=None,
    link=None,
)]


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings', [{
    'include_crypto2crypto': False,
    'include_fees_in_cost_basis': False,
}])
def test_nocrypto2crypto(accountant, google_service):
    accounting_history_process(accountant, 1436979735, 1519693374, history5)
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=ZERO, free=FVal('264693.433642820')),
        AccountingEventType.FEE: PNL(taxable=FVal('-0.238868129979988140934107'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings', [{
    'taxfree_after_period': -1,
    'include_fees_in_cost_basis': False,
}])
def test_no_taxfree_period(accountant, google_service):
    accounting_history_process(accountant, 1436979735, 1519693374, history5)
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=FVal('265253.1344345727833875'), free=ZERO),
        AccountingEventType.FEE: PNL(taxable=FVal('-0.238868129979988140934107'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings', [{
    'taxfree_after_period': 86400,
    'include_fees_in_cost_basis': False,
}])
def test_big_taxfree_period(accountant, google_service):
    accounting_history_process(accountant, 1436979735, 1519693374, history5)
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=ZERO, free=FVal('265253.1344345727833875')),
        AccountingEventType.FEE: PNL(
            taxable=FVal('-1.170993974737499896599075038'),
            free=FVal('0.9321258447575117556649680375'),
        ),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('ignored_assets', [[A_DASH]])
@pytest.mark.parametrize('db_settings', [{'include_gas_costs': True}, {'include_gas_costs': False}])  # noqa: E501
def test_include_gas_costs(accountant, google_service):
    addr1 = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'
    tx_hash = deserialize_evm_tx_hash('0x5cc0e6e62753551313412492296d5e57bea0a9d1ce507cc96aa4aa076c5bde7a')  # noqa: E501
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
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=1569924574000,
            location=Location.ETHEREUM,
            location_label=addr1,
            asset=A_ETH,
            amount=FVal('0.000030921'),
            notes='Burn 0.000030921 ETH for gas',
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
@pytest.mark.parametrize('db_settings', [{'include_fees_in_cost_basis': False}])
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
        AccountingEventType.TRADE: PNL(taxable=FVal('559.7007917527833875'), free=ZERO),
        AccountingEventType.FEE: PNL(taxable=FVal('-0.238868129979988140934107'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings', [{'include_fees_in_cost_basis': False}])
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
    assert get_calculated_asset_amount(accountant.pots[0].cost_basis, A_BTC).is_close('3.7468')
    expected_pnls = PnlTotals({
        AccountingEventType.TRADE: PNL(taxable=FVal('1941.115'), free=ZERO),
        AccountingEventType.FEE: PNL(taxable=FVal('-1.8712160'), free=ZERO),
        AccountingEventType.MARGIN_POSITION: PNL(taxable=FVal('-44.405'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize(('db_settings', 'expected'), [
    (
        {
            'calculate_past_cost_basis': False,
            'taxfree_after_period': -1,
            'include_fees_in_cost_basis': False,
        },
        PnlTotals({
            AccountingEventType.TRADE: PNL(taxable=FVal('2292.44'), free=ZERO),
            AccountingEventType.FEE: PNL(taxable=FVal('-0.01'), free=ZERO),
        }),
    ),
    (
        {
            'calculate_past_cost_basis': True,
            'taxfree_after_period': -1,
            'include_fees_in_cost_basis': False,
        },
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


@pytest.mark.skipif(
    'CI' in os.environ,
    reason='It needs to be updated in rotki/rotki/issues/7508',
)
@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('accountant_without_rules', [True])
@pytest.mark.parametrize('staking_taxable', [True, False])
def test_eth_withdrawal_not_taxable(accountant: Accountant, staking_taxable: bool) -> None:
    """Test that eth withdrawal events respect the accounting rules"""
    db = DBAccountingRules(accountant.db)
    db.add_accounting_rule(
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        counterparty=None,
        rule=BaseEventSettings(
            taxable=staking_taxable,
            count_entire_amount_spend=False,
            count_cost_basis_pnl=False,
            accounting_treatment=None,
        ),
        links={},
    )

    staking_reward = FVal('0.017197')
    history = [
        EthWithdrawalEvent(
            identifier=3,
            validator_index=1,
            timestamp=TimestampMS(1699319051000),
            amount=staking_reward,
            withdrawal_address=make_evm_address(),
            is_exit=False,
        ),
    ]

    accounting_history_process(
        accountant=accountant,
        start_ts=Timestamp(1699319041),
        end_ts=Timestamp(1699319061),
        history_list=history,
    )
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({
        AccountingEventType.HISTORY_EVENT: PNL(
            taxable=staking_reward if staking_taxable else ZERO,
            free=ZERO,
        ),
    })

    pnls = accountant.pots[0].pnls
    assert_pnl_totals_close(expected=expected_pnls, got=pnls)


@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('accountant_without_rules', [True])
@pytest.mark.parametrize(('db_settings', 'is_staking_taxable'), [
    ({'eth_staking_taxable_after_withdrawal_enabled': False}, False),
    ({'eth_staking_taxable_after_withdrawal_enabled': True}, True),
])
def test_eth_withdrawal_respects_db_settings(
        accountant: Accountant,
        is_staking_taxable: bool,
) -> None:
    """Test that eth withdrawal events respect the user settings regarding taxation"""
    staking_reward = FVal('0.017197')
    history = [
        EthWithdrawalEvent(
            identifier=3,
            validator_index=1,
            timestamp=TimestampMS(1699319051000),
            amount=staking_reward,
            withdrawal_address=make_evm_address(),
            is_exit=False,
        ),
    ]

    accountant.pots[0].events_accountant.reset()
    accounting_history_process(
        accountant=accountant,
        start_ts=Timestamp(1699319041),
        end_ts=Timestamp(1699319061),
        history_list=history,
    )
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({
        AccountingEventType.HISTORY_EVENT: PNL(
            taxable=staking_reward if is_staking_taxable else ZERO,
            free=ZERO,
        ),
    })

    pnls = accountant.pots[0].pnls
    assert_pnl_totals_close(expected=expected_pnls, got=pnls)
