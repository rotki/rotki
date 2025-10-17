from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.chain.evm.decoding.paraswap.constants import CPT_PARASWAP
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH, A_WBTC
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.accounting import accounting_history_process, assert_pnl_totals_close
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.tests.utils.messages import no_message_errors
from rotkehlchen.types import Location, Price, Timestamp, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.accounting.accountant import Accountant


@pytest.mark.parametrize('mocked_price_queries', [{
    A_WBTC.identifier: {'EUR': {
        Timestamp(1700000000): Price(FVal(5)),
        Timestamp(1700000001): Price(FVal(10)),
    }},
    A_ETH.identifier: {'EUR': {
        Timestamp(1700000000): Price(FVal(0.1)),
        Timestamp(1700000001): Price(FVal(0.1)),
    }},
}])
@pytest.mark.parametrize('accounting_initialize_parameters', [True])
@pytest.mark.parametrize('db_settings', [
    {'include_fees_in_cost_basis': True},
    {'include_fees_in_cost_basis': False},
])
def test_paraswap_swap_with_fee(accountant: 'Accountant', db_settings: dict):
    """Test that the fee in paraswap is handled correctly during accounting"""
    tx_hash, user_address, contract_address, acquired_from_address, swap_amount_str, fee_amount_str, receive_amount_str = make_evm_tx_hash(), make_evm_address(), make_evm_address(), make_evm_address(), '1', '1', '100'  # noqa: E501
    events = [EvmEvent(  # this event is to create cost basis for wBTC
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(1700000000000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_WBTC,
        amount=FVal(swap_amount_str),
        location_label=user_address,
        notes=f'Receive {swap_amount_str} WBTC from {acquired_from_address} to {user_address}',
        counterparty='0xrandomaddress',
        address=acquired_from_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=TimestampMS(1700000001000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_WBTC,
        amount=FVal(swap_amount_str),
        location_label=user_address,
        notes=f'Swap {swap_amount_str} WBTC in paraswap',
        counterparty=CPT_PARASWAP,
        address=contract_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=TimestampMS(1700000001000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal(receive_amount_str),
        location_label=user_address,
        notes=f'Receive {receive_amount_str} ETH as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=contract_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=TimestampMS(1700000001000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(fee_amount_str),
        location_label=user_address,
        notes=f'Spend {fee_amount_str} ETH as a paraswap fee',
        counterparty=CPT_PARASWAP,
        address=contract_address,
    )]

    accounting_history_process(
        accountant=accountant,
        start_ts=Timestamp(1700000000),
        end_ts=Timestamp(1700000001),
        history_list=events,
    )
    no_message_errors(accountant.msg_aggregator)

    fee_spent_event = accountant.pots[0].processed_events[3]
    if db_settings['include_fees_in_cost_basis']:
        expected_pnls = PnlTotals({
            AccountingEventType.TRANSACTION_EVENT: PNL(taxable=FVal(10), free=ZERO),  # Get BTC(€5) + profit_from_selling_btc(€5)  # noqa: E501
        })
        assert fee_spent_event.price == Price(FVal(0.101))  # (Fee given(€0.1) + BTC swapped(€10)) / ETH received(100)  # noqa: E501
        assert fee_spent_event.cost_basis is None  # Fee is not taxable, because it is not included in cost basis  # noqa: E501
    else:
        expected_pnls = PnlTotals({
            AccountingEventType.TRANSACTION_EVENT: PNL(taxable=FVal(10), free=ZERO),  # Get BTC(€5) + profit_from_selling_btc(€5)  # noqa: E501
            AccountingEventType.FEE: PNL(taxable=FVal(-0.1), free=ZERO),  # -one_eth_fee(0.1)
        })
        assert fee_spent_event.price == Price(FVal(0.1))  # BTC swapped(€10) / ETH received(€100)
        assert fee_spent_event.cost_basis is not None  # Fee is taxable this time
        assert fee_spent_event.cost_basis.taxable_amount == ONE
        assert fee_spent_event.cost_basis.taxable_bought_cost == FVal(0.1)  # BTC swapped(€10) / ETH received(€100)  # noqa: E501
    assert_pnl_totals_close(expected_pnls, accountant.pots[0].pnls)
