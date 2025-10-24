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
from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
from rotkehlchen.chain.evm.decoding.thegraph.constants import CPT_THEGRAPH
from rotkehlchen.constants.assets import A_GRT
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import Location, Price, Timestamp
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.accounting.accountant import Accountant

TS1, TS2, TS3 = Timestamp(1704200595), Timestamp(1704201595), Timestamp(1704202595)
TSMS1, TSMS2, TSMS3 = ts_sec_to_ms(TS1), ts_sec_to_ms(TS2), ts_sec_to_ms(TS3)
USER_ADDRESS = make_evm_address()
HASH1, HASH2, HASH3 = make_evm_tx_hash(), make_evm_tx_hash(), make_evm_tx_hash()


@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('accounting_initialize_parameters', [True])
def test_delegation_reward(accountant: 'Accountant'):
    pot = accountant.pots[0]
    events_iterator = peekable([EvmEvent(
        tx_ref=HASH1,
        sequence_index=358,
        timestamp=TSMS1,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_GRT,
        amount=FVal('1000'),
        location_label=USER_ADDRESS,
        notes='Acquire 1000 GRT',
        counterparty=None,
        address=None,
    ), EvmEvent(
        tx_ref=HASH2,
        sequence_index=359,
        timestamp=TSMS2,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=A_GRT,
        amount=FVal('995'),
        location_label=USER_ADDRESS,
        notes='Delegate 995 GRT to indexer',
        counterparty=CPT_THEGRAPH,
        address=None,
    ), EvmEvent(
        tx_ref=HASH2,
        sequence_index=360,
        timestamp=TSMS2,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_GRT,
        amount=FVal('5'),
        location_label=USER_ADDRESS,
        notes='Burn 5 GRT as delegation tax',
        counterparty=CPT_THEGRAPH,
        address=None,
    ), EvmEvent(
        tx_ref=HASH3,
        sequence_index=208,
        timestamp=TSMS3,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=A_GRT,
        amount=FVal('1005'),
        location_label=USER_ADDRESS,
        notes='Withdraw 1005 GRT from indexer',
        counterparty=CPT_THEGRAPH,
        address=None,
    )])
    for event in events_iterator:
        pot.events_accountant.process(event=event, events_iterator=events_iterator)  # type: ignore

    matched_acquisitions = [MatchedAcquisition(
        amount=FVal('5'),
        event=AssetAcquisitionEvent(amount=FVal('1000'), timestamp=TS1, rate=Price(ONE), index=0),
        taxable=True,
    )]
    matched_acquisitions[0].event.remaining_amount = FVal('995')  # can't be set by init
    expected_events = [
        ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes='Acquire 1000 GRT',
            location=Location.ETHEREUM,
            timestamp=TS1,
            asset=A_GRT,
            free_amount=ZERO,
            taxable_amount=FVal('1000'),
            price=Price(ONE),
            pnl=PNL(taxable=FVal(1000), free=ZERO),
            cost_basis=None,
            index=0,
            extra_data={'tx_ref': str(HASH1)},
        ), ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes='Delegate 995 GRT to indexer',
            location=Location.ETHEREUM,
            timestamp=TS2,
            asset=A_GRT,
            free_amount=FVal('995'),
            taxable_amount=ZERO,
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),  # Deposits are not taxable
            cost_basis=None,
            index=1,
            extra_data={'tx_ref': str(HASH2)},
        ), ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes='Burn 5 GRT as delegation tax',
            location=Location.ETHEREUM,
            timestamp=TS2,
            asset=A_GRT,
            free_amount=ZERO,
            taxable_amount=FVal('5'),
            price=Price(ONE),
            pnl=PNL(taxable=FVal('-5'), free=ZERO),
            cost_basis=CostBasisInfo(
                taxable_amount=FVal('5'),
                taxable_bought_cost=FVal('5'),
                taxfree_bought_cost=ZERO,
                matched_acquisitions=matched_acquisitions,
                is_complete=True,
            ),
            index=2,
            extra_data={'tx_ref': str(HASH2)},
        ), ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes=f'Gained 10 GRT as delegation reward for {USER_ADDRESS}',
            location=Location.ETHEREUM,
            timestamp=TS3,
            asset=A_GRT,
            free_amount=ZERO,
            taxable_amount=FVal('10'),
            price=Price(ONE),
            pnl=PNL(taxable=FVal('10'), free=ZERO),
            cost_basis=None,
            index=3,
            extra_data={'tx_ref': str(HASH3)},
        ), ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes='Withdraw 1005 GRT from indexer',
            location=Location.ETHEREUM,
            timestamp=TS3,
            asset=A_GRT,
            free_amount=FVal('1005'),
            taxable_amount=ZERO,
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),
            cost_basis=None,
            index=4,
            extra_data={'tx_ref': str(HASH3)},
        ),
    ]
    expected_events[0].count_cost_basis_pnl = True  # can't be set by init()
    expected_events[2].count_cost_basis_pnl = True  # can't be set by init()
    expected_events[2].count_entire_amount_spend = True  # can't be set by init()
    expected_events[3].count_cost_basis_pnl = True  # can't be set by init()
    assert pot.processed_events == expected_events
