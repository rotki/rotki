from typing import TYPE_CHECKING

import pytest
from more_itertools import peekable

from rotkehlchen.accounting.cost_basis.base import (
    AssetAcquisitionEvent,
    CostBasisInfo,
    MatchedAcquisition,
)
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
from rotkehlchen.chain.evm.decoding.paraswap.constants import CPT_PARASWAP
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_USDC, A_WBTC
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.accounting import (
    MOCKED_PRICES,
    TIMESTAMP_0_MS,
    TIMESTAMP_0_SEC,
    TIMESTAMP_1_MS,
    TIMESTAMP_1_SEC,
)
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import Location, Price

if TYPE_CHECKING:
    from rotkehlchen.accounting.accountant import Accountant


@pytest.mark.parametrize('mocked_price_queries', [MOCKED_PRICES])
@pytest.mark.parametrize('accounting_initialize_parameters', [True])
def test_paraswap_swap_with_fee(accountant: 'Accountant'):
    """Test that the fee in paraswap is handled correctly during accounting"""
    tx_hash, user_address, contract_address, aquired_from_address, swap_amount_str, fee_amount_str, receive_amount_str = make_evm_tx_hash(), make_evm_address(), make_evm_address(), make_evm_address(), '138.2851', '11.308417', '1190.359719'  # noqa: E501
    events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=TIMESTAMP_0_MS,  # half price at t=0
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_WBTC,
        balance=Balance(amount=FVal(swap_amount_str)),
        location_label=user_address,
        notes=f'Receive {swap_amount_str} WBTC from {aquired_from_address} to {user_address}',
        counterparty=CPT_PARASWAP,
        address=aquired_from_address,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=TIMESTAMP_0_MS,  # same price at t=0
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_USDC,
        balance=Balance(amount=ONE),
        location_label=user_address,
        notes=f'Receive {ONE} USDC from {aquired_from_address} to {user_address}',
        counterparty=CPT_PARASWAP,
        address=aquired_from_address,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_WBTC,
        balance=Balance(amount=FVal(swap_amount_str)),
        location_label=user_address,
        notes=f'Swap {swap_amount_str} WBTC in paraswap',
        counterparty=CPT_PARASWAP,
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
        notes=f'Receive {receive_amount_str} USDC as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=contract_address,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=4,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USDC,
        balance=Balance(amount=FVal(fee_amount_str)),
        location_label=user_address,
        notes=f'Spend {fee_amount_str} USDC as a paraswap fee',
        counterparty=CPT_PARASWAP,
        address=contract_address,
    )]
    pot = accountant.pots[0]
    events_iterator = peekable(events)
    for event in events_iterator:
        pot.events_accountant.process(event=event, events_iterator=events_iterator)  # type: ignore

    extra_data = {
        'group_id': '1' + tx_hash.hex() + '23',  # pylint: disable=no-member
        'tx_hash': tx_hash.hex(),  # pylint: disable=no-member
    }
    wbtc_prices = MOCKED_PRICES[A_WBTC.identifier]['EUR']
    aquisition_event = AssetAcquisitionEvent(
        index=0,
        timestamp=TIMESTAMP_0_SEC,
        amount=FVal(swap_amount_str),
        rate=wbtc_prices[TIMESTAMP_0_SEC],
    )
    aquisition_event.remaining_amount = ZERO  # since it's not settable at ctor
    expected_processed_events = [
        ProcessedAccountingEvent(
            index=0,
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes=f'Receive {swap_amount_str} WBTC from {aquired_from_address} to {user_address}',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_0_SEC,
            asset=A_WBTC,
            free_amount=ZERO,
            taxable_amount=events[0].balance.amount,
            price=wbtc_prices[TIMESTAMP_0_SEC],
            pnl=PNL(taxable=events[0].balance.amount * wbtc_prices[TIMESTAMP_0_SEC], free=ZERO),
            cost_basis=None,
            extra_data={'tx_hash': tx_hash.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            index=1,
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes=f'Receive {ONE} USDC from {aquired_from_address} to {user_address}',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_0_SEC,
            asset=A_USDC,
            free_amount=ZERO,
            taxable_amount=ONE,
            price=Price(ONE),
            pnl=PNL(taxable=ONE, free=ZERO),
            cost_basis=None,
            extra_data={'tx_hash': tx_hash.hex()},  # pylint: disable=no-member
        ),
        ProcessedAccountingEvent(
            index=2,
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes=f'Swap {swap_amount_str} WBTC in paraswap',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SEC,
            asset=A_WBTC,
            free_amount=ZERO,
            taxable_amount=events[2].balance.amount,
            price=Price(ONE),
            pnl=PNL(taxable=events[2].balance.amount * wbtc_prices[TIMESTAMP_1_SEC] - aquisition_event.amount * wbtc_prices[TIMESTAMP_0_SEC], free=ZERO),  # noqa: E501
            cost_basis=CostBasisInfo(
                taxable_amount=events[2].balance.amount,
                taxable_bought_cost=events[2].balance.amount * wbtc_prices[TIMESTAMP_1_SEC] - aquisition_event.amount * wbtc_prices[TIMESTAMP_0_SEC],  # noqa: E501
                taxfree_bought_cost=ZERO,
                is_complete=True,
                matched_acquisitions=[MatchedAcquisition(
                    taxable=True,
                    amount=aquisition_event.amount,
                    event=aquisition_event,
                )],
            ),
            extra_data=extra_data,
        ), ProcessedAccountingEvent(
            index=3,
            event_type=AccountingEventType.FEE,
            notes=f'Spend {fee_amount_str} USDC as a paraswap fee',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SEC,
            asset=A_USDC,
            free_amount=ZERO,
            taxable_amount=FVal(fee_amount_str),
            price=Price((FVal(swap_amount_str) + FVal(fee_amount_str)) / FVal(receive_amount_str)),
            pnl=PNL(taxable=ZERO, free=ZERO),
            cost_basis=None,
            extra_data=extra_data,
        ), ProcessedAccountingEvent(
            index=4,
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes=f'Receive {receive_amount_str} USDC as the result of a swap in paraswap',
            location=Location.ETHEREUM,
            timestamp=TIMESTAMP_1_SEC,
            asset=A_USDC,
            free_amount=FVal(receive_amount_str),
            taxable_amount=ZERO,
            price=Price((FVal(swap_amount_str) + FVal(fee_amount_str)) / FVal(receive_amount_str)),
            pnl=PNL(taxable=ZERO, free=ZERO),
            cost_basis=None,
            extra_data=extra_data,
        )]
    expected_processed_events[0].count_cost_basis_pnl = True  # since it's not settable at ctor
    expected_processed_events[1].count_cost_basis_pnl = True  # since it's not settable at ctor
    expected_processed_events[2].count_cost_basis_pnl = True  # since it's not settable at ctor
    assert pot.processed_events == expected_processed_events
    assert pot.pnls[AccountingEventType.TRANSACTION_EVENT].taxable == events[0].balance.amount + events[1].balance.amount  # noqa: E501
    assert pot.pnls[AccountingEventType.TRANSACTION_EVENT].total == events[0].balance.amount + events[1].balance.amount  # noqa: E501
