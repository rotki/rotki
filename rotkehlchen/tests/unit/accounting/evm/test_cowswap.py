from typing import TYPE_CHECKING

import pytest
from more_itertools import peekable

from rotkehlchen.accounting.cost_basis.base import CostBasisInfo
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL
from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
from rotkehlchen.chain.evm.decoding.cowswap.constants import CPT_COWSWAP
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_USDC, A_WBTC
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.accounting import MOCKED_PRICES, TIMESTAMP_1_MS, TIMESTAMP_1_SEC
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import Location, Price

if TYPE_CHECKING:
    from rotkehlchen.accounting.accountant import Accountant


@pytest.mark.parametrize('mocked_price_queries', [MOCKED_PRICES])
@pytest.mark.parametrize('accounting_initialize_parameters', [True])
def test_cowswap_swap_with_fee(accountant: 'Accountant'):
    """Test that the fee in cowswap is handled correctly during accounting"""
    tx_hash = make_evm_tx_hash()
    user_address = make_evm_address()
    contract_address = make_evm_address()
    swap_amount_str = '0.99'
    fee_amount_str = '0.01'
    receive_amount_str = '10000'
    events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=TIMESTAMP_1_MS,
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
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDC,
        amount=FVal(receive_amount_str),
        location_label=user_address,
        notes=f'Receive {receive_amount_str} USDC as the result of a swap in cowswap',
        counterparty=CPT_COWSWAP,
        address=contract_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_WBTC,
        amount=FVal(fee_amount_str),
        location_label=user_address,
        notes=f'Spend {fee_amount_str} WBTC as a cowswap fee',
        counterparty=CPT_COWSWAP,
        address=contract_address,
    )]
    pot = accountant.pots[0]
    events_iterator = peekable(events)
    for event in events_iterator:
        pot.events_accountant.process(event=event, events_iterator=events_iterator)  # type: ignore

    extra_data = {
        'group_id': '1' + str(tx_hash) + '12',
        'tx_ref': str(tx_hash),
    }
    expected_processed_events = [
        ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes=f'Swap {swap_amount_str} WBTC in cowswap',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SEC,
            asset=A_WBTC,
            free_amount=ZERO,
            taxable_amount=FVal(swap_amount_str),
            price=Price(ONE),
            pnl=PNL(taxable=FVal(swap_amount_str), free=ZERO),
            cost_basis=CostBasisInfo(taxable_amount=FVal(swap_amount_str), taxable_bought_cost=ZERO, taxfree_bought_cost=ZERO, matched_acquisitions=[], is_complete=False),  # noqa: E501
            index=0,
            extra_data=extra_data,
        ), ProcessedAccountingEvent(
            event_type=AccountingEventType.FEE,
            notes=f'Spend {fee_amount_str} WBTC as a cowswap fee',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SEC,
            asset=A_WBTC,
            free_amount=FVal(fee_amount_str),
            taxable_amount=ZERO,
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),
            cost_basis=None,
            index=1,
            extra_data=extra_data,
        ), ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes=f'Receive {receive_amount_str} USDC as the result of a swap in cowswap',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SEC,
            asset=A_USDC,
            free_amount=FVal(receive_amount_str),
            taxable_amount=ZERO,
            price=Price(FVal('0.0001')),
            pnl=PNL(taxable=ZERO, free=ZERO),
            cost_basis=None,
            index=2,
            extra_data=extra_data,
        )]
    expected_processed_events[0].count_cost_basis_pnl = True  # since it's not settable at ctor
    assert pot.processed_events == expected_processed_events
