from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.cost_basis.base import CostBasisInfo
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.decoding.cowswap.constants import CPT_COWSWAP
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_USDC, A_WBTC
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import Location, Price, Timestamp, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.accounting.accountant import Accountant

TIMESTAMP_1_MS = TimestampMS(1000)
TIMESTAMP_1_SEC = Timestamp(1)

MOCKED_PRICES = {
    A_WBTC.identifier: {
        'EUR': {
            TIMESTAMP_1_SEC: Price(ONE),
        },
    },
    A_USDC.identifier: {
        'EUR': {
            TIMESTAMP_1_SEC: Price(ONE),
        },
    },
}


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
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_WBTC,
        balance=Balance(amount=FVal(swap_amount_str)),
        location_label=user_address,
        notes=f'Swap {swap_amount_str} WBTC in cowswap',
        counterparty=CPT_COWSWAP,
        address=contract_address,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_WBTC,
        balance=Balance(amount=FVal(fee_amount_str)),
        location_label=user_address,
        notes=f'Spend {fee_amount_str} WBTC as a cowswap fee',
        counterparty=CPT_COWSWAP,
        address=contract_address,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDC,
        balance=Balance(amount=FVal(receive_amount_str)),
        location_label=user_address,
        notes=f'Receive {receive_amount_str} USDC as the result of a swap in cowswap',
        counterparty=CPT_COWSWAP,
        address=contract_address,
    )]
    pot = accountant.pots[0]
    events_iterator = iter(events)
    for event in events_iterator:
        pot.events_accountant.process(event=event, events_iterator=events_iterator)

    extra_data = {
        'group_id': '1' + tx_hash.hex() + '13',  # pylint: disable=no-member
        'tx_hash': tx_hash.hex(),  # pylint: disable=no-member
    }
    expected_processed_events = [
        ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
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
            type=AccountingEventType.FEE,
            notes=f'Spend {fee_amount_str} WBTC as a cowswap fee',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SEC,
            asset=A_WBTC,
            free_amount=ZERO,
            taxable_amount=FVal(fee_amount_str),
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),
            cost_basis=None,
            index=1,
            extra_data=extra_data,
        ), ProcessedAccountingEvent(
            type=AccountingEventType.TRANSACTION_EVENT,
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
