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
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE_V2
from rotkehlchen.constants.assets import A_DAI, A_REN
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import Location, Price, Timestamp
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.accounting.accountant import Accountant

TS1, TS2 = Timestamp(1704201595), Timestamp(1704202595)  # random timestamps not near 0
TSMS1, TSMS2 = ts_sec_to_ms(TS1), ts_sec_to_ms(TS2)
USER_ADDRESS = make_evm_address()
HASH1, HASH2 = make_evm_tx_hash(), make_evm_tx_hash()


@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('accounting_initialize_parameters', [True])
def test_v2_withdraw(accountant: 'Accountant'):
    pot = accountant.pots[0]
    events_iterator = peekable([EvmEvent(
        tx_ref=HASH1,
        sequence_index=0,
        timestamp=TSMS1,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_DAI,
        amount=FVal('1000'),
        location_label=USER_ADDRESS,
        notes='Deposit 1000 DAI into AAVE v2',
        counterparty=CPT_AAVE_V2,
    ), EvmEvent(
        tx_ref=HASH1,
        sequence_index=2,
        timestamp=TSMS1,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:1/erc20:0x028171bCA77440897B824Ca71D1c56caC55b68A3'),
        amount=FVal('1000'),
        location_label=USER_ADDRESS,
        notes='Receive 1000 aDAI from AAVE v2',
        counterparty=CPT_AAVE_V2,
    ), EvmEvent(
        tx_ref=HASH2,
        sequence_index=0,
        timestamp=TSMS2,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=Asset('eip155:1/erc20:0x028171bCA77440897B824Ca71D1c56caC55b68A3'),
        amount=FVal('1050'),
        location_label=USER_ADDRESS,
        notes='Return 1050 aDAI to AAVE v2',
        counterparty=CPT_AAVE_V2,
    ), EvmEvent(
        tx_ref=HASH2,
        sequence_index=2,
        timestamp=TSMS2,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_DAI,
        amount=FVal('1050'),
        location_label=USER_ADDRESS,
        notes='Withdraw 1050 DAI from AAVE v2',
        counterparty=CPT_AAVE_V2,
    )])
    for event in events_iterator:
        pot.events_accountant.process(event=event, events_iterator=events_iterator)  # type: ignore

    expected_events = [
        ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes='Deposit 1000 DAI into AAVE v2',
            location=Location.ETHEREUM,
            timestamp=TS1,
            asset=A_DAI,
            free_amount=FVal(1000),
            taxable_amount=ZERO,
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),
            cost_basis=None,
            index=0,
            extra_data={'tx_ref': str(HASH1)},
        ), ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes='Receive 1000 aDAI from AAVE v2',
            location=Location.ETHEREUM,
            timestamp=TS1,
            asset=Asset('eip155:1/erc20:0x028171bCA77440897B824Ca71D1c56caC55b68A3'),
            free_amount=FVal(1000),
            taxable_amount=ZERO,
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),
            cost_basis=None,
            index=1,
            extra_data={'tx_ref': str(HASH1)},
        ), ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes='Return 1050 aDAI to AAVE v2',
            location=Location.ETHEREUM,
            timestamp=TS2,
            asset=Asset('eip155:1/erc20:0x028171bCA77440897B824Ca71D1c56caC55b68A3'),
            free_amount=FVal(1050),
            taxable_amount=ZERO,
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),
            cost_basis=None,
            index=2,
            extra_data={'tx_ref': str(HASH2)},
        ), ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes=f'Gained 50 DAI on Aave v2 as interest rate for {USER_ADDRESS}',
            location=Location.ETHEREUM,
            timestamp=TS2,
            asset=A_DAI,
            free_amount=ZERO,
            taxable_amount=FVal(50),
            price=Price(ONE),
            pnl=PNL(taxable=FVal(50), free=ZERO),  # $50 interest gained
            cost_basis=None,
            index=3,
            extra_data={'tx_ref': str(HASH2)},
        ), ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes='Withdraw 1050 DAI from AAVE v2',
            location=Location.ETHEREUM,
            timestamp=TS2,
            asset=A_DAI,
            free_amount=FVal(1050),
            taxable_amount=ZERO,
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),
            cost_basis=None,
            index=4,
            extra_data={'tx_ref': str(HASH2)},
        ),
    ]
    expected_events[3].count_cost_basis_pnl = True  # can't be set by init()
    assert pot.processed_events == expected_events


@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('accounting_initialize_parameters', [True])
def test_v2_payback(accountant: 'Accountant'):
    pot = accountant.pots[0]
    events_iterator = peekable([EvmEvent(
        tx_ref=HASH1,
        sequence_index=0,
        timestamp=TSMS1,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:1/erc20:0xcd9D82d33bd737De215cDac57FE2F7f04DF77FE0'),
        amount=FVal('1000'),
        location_label=USER_ADDRESS,
        notes='Receive 1000 variableDebtREN from AAVE v2',
        counterparty=CPT_AAVE_V2,
    ), EvmEvent(
        tx_ref=HASH1,
        sequence_index=2,
        timestamp=TSMS1,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.GENERATE_DEBT,
        asset=A_REN,
        amount=FVal('1000'),
        location_label=USER_ADDRESS,
        notes='Borrow 1000 REN from AAVE v2 with variable APY 0.80%',
        counterparty=CPT_AAVE_V2,
    ), EvmEvent(
        tx_ref=HASH2,
        sequence_index=0,
        timestamp=TSMS2,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=Asset('eip155:1/erc20:0xcd9D82d33bd737De215cDac57FE2F7f04DF77FE0'),
        amount=FVal('1050'),
        location_label=USER_ADDRESS,
        notes='Return 1050 variableDebtREN to AAVE v2',
        counterparty=CPT_AAVE_V2,
    ), EvmEvent(
        tx_ref=HASH2,
        sequence_index=2,
        timestamp=TSMS2,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.PAYBACK_DEBT,
        asset=A_REN,
        amount=FVal('1050'),
        location_label=USER_ADDRESS,
        notes='Repay 1050 REN on AAVE v2',
        counterparty=CPT_AAVE_V2,
    )])
    for event in events_iterator:
        pot.events_accountant.process(event=event, events_iterator=events_iterator)  # type: ignore

    matched_acquisitions = [MatchedAcquisition(
        amount=FVal(50),
        event=AssetAcquisitionEvent(amount=FVal(1000), timestamp=TS1, rate=Price(ONE), index=1),
        taxable=True,
    )]
    matched_acquisitions[0].event.remaining_amount = FVal(950)  # can't be set by init
    expected_events = [
        ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes='Receive 1000 variableDebtREN from AAVE v2',
            location=Location.ETHEREUM,
            timestamp=TS1,
            asset=Asset('eip155:1/erc20:0xcd9D82d33bd737De215cDac57FE2F7f04DF77FE0'),
            free_amount=FVal(1000),
            taxable_amount=ZERO,
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),
            cost_basis=None,
            index=0,
            extra_data={'tx_ref': str(HASH1)},
        ), ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes='Borrow 1000 REN from AAVE v2 with variable APY 0.80%',
            location=Location.ETHEREUM,
            timestamp=TS1,
            asset=A_REN,
            free_amount=FVal(1000),
            taxable_amount=ZERO,
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),
            cost_basis=None,
            index=1,
            extra_data={'tx_ref': str(HASH1)},
        ), ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes='Return 1050 variableDebtREN to AAVE v2',
            location=Location.ETHEREUM,
            timestamp=TS2,
            asset=Asset('eip155:1/erc20:0xcd9D82d33bd737De215cDac57FE2F7f04DF77FE0'),
            free_amount=FVal(1050),
            taxable_amount=ZERO,
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),
            cost_basis=None,
            index=2,
            extra_data={'tx_ref': str(HASH2)},
        ), ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes=f'Lost 50 REN as debt during payback to Aave v2 loan for {USER_ADDRESS}',
            location=Location.ETHEREUM,
            timestamp=TS2,
            asset=A_REN,
            free_amount=ZERO,
            taxable_amount=FVal(50),
            price=Price(ONE),
            pnl=PNL(taxable=FVal(-50), free=ZERO),  # $50 loss in interest for payback
            cost_basis=CostBasisInfo(
                taxable_amount=FVal(50),
                taxable_bought_cost=FVal(50),
                taxfree_bought_cost=ZERO,
                matched_acquisitions=matched_acquisitions,
                is_complete=True,
            ),
            index=3,
            extra_data={'tx_ref': str(HASH2)},
        ), ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes='Repay 1050 REN on AAVE v2',
            location=Location.ETHEREUM,
            timestamp=TS2,
            asset=A_REN,
            free_amount=FVal(1050),
            taxable_amount=ZERO,
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=ZERO),
            cost_basis=None,
            index=4,
            extra_data={'tx_ref': str(HASH2)},
        ),
    ]
    expected_events[3].count_cost_basis_pnl = True  # can't be set by init()
    expected_events[3].count_entire_amount_spend = True  # can't be set by init()
    assert pot.processed_events == expected_events
