from typing import TYPE_CHECKING, Any, Literal

import pytest
from more_itertools import peekable

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.accounting.cost_basis.base import (
    AssetAcquisitionEvent,
    CostBasisInfo,
    MatchedAcquisition,
)
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL
from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.chain.evm.decoding.weth.constants import CPT_WETH
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_WETH
from rotkehlchen.db.accounting_rules import DBAccountingRules
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import Location, Price, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.accounting.history_base_entries import EventsAccountant
    from rotkehlchen.accounting.pot import AccountingPot

EXAMPLE_EVM_HASH = make_evm_tx_hash()
EXAMPLE_TX_HASH_HEX = str(EXAMPLE_EVM_HASH)
EXAMPLE_ADDRESS = make_evm_address()

# Some utility timestamps. They are used for mocked prices.
TIMESTAMP_1_SECS = Timestamp(1624395186)
TIMESTAMP_1_MS = ts_sec_to_ms(TIMESTAMP_1_SECS)
TIMESTAMP_2_SECS = Timestamp(1628994441)
TIMESTAMP_2_MS = ts_sec_to_ms(TIMESTAMP_2_SECS)

ETH_PRICE_TS_1 = FVal('2000')
ETH_PRICE_TS_2 = FVal('3000')

MOCKED_PRICES = {
    'ETH': {
        'EUR': {
            TIMESTAMP_1_SECS: ETH_PRICE_TS_1,
            TIMESTAMP_2_SECS: ETH_PRICE_TS_2,
        },
    },
    A_DAI.identifier: {
        'EUR': {
            TIMESTAMP_2_SECS: Price(ONE),
        },
    },
}


@pytest.fixture(name='gas_taxable')
def fixture_gas_taxable():
    return True


@pytest.fixture(name='include_crypto2crypto')
def fixture_include_crypto2crypto():
    return True


@pytest.fixture(name='accounting_pot')
def fixture_accounting_pot(
        accountant: Accountant,
        gas_taxable: bool,
        include_crypto2crypto: bool,
):
    pot = accountant.pots[0]
    with pot.database.user_write() as write_cursor:
        pot.database.set_settings(
            write_cursor=write_cursor,
            settings=ModifiableDBSettings(
                include_gas_costs=gas_taxable,
                include_crypto2crypto=include_crypto2crypto,
            ),
        )
    with pot.database.conn.read_ctx() as cursor:
        settings = pot.database.get_settings(cursor)
    pot.reset(
        settings=settings,
        start_ts=Timestamp(0),  # timestamps don't matter since they are used only for querying
        end_ts=Timestamp(0),  # history, which does not happen in the tests in this file
        report_id=1,
    )
    return pot


def _gain_one_ether(
        events_accountant: 'EventsAccountant',
        event_type: 'HistoryEventType' = HistoryEventType.RECEIVE,
        event_subtype: 'HistoryEventSubType' = HistoryEventSubType.NONE,
        entry_type: Literal['history_event', 'evm_event'] = 'evm_event',
) -> None:
    """Helper function to gain 1 ETH, so that spending events have something to spend"""
    event_class: type[HistoryEvent | EvmEvent]
    kwargs: dict[str, Any]
    if entry_type == 'history_event':
        event_class = HistoryEvent
        kwargs = {'group_identifier': f'rotki_events_{EXAMPLE_TX_HASH_HEX}'}
    else:  # can only be evm event
        event_class = EvmEvent
        kwargs = {'tx_ref': EXAMPLE_EVM_HASH}

    eth_gain_event = event_class(
        **kwargs,
        sequence_index=0,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        location_label=EXAMPLE_ADDRESS,
        asset=A_ETH,
        amount=ONE,
        notes='Received 1 ETH',
        event_type=event_type,
        event_subtype=event_subtype,
    )
    consumed_num = events_accountant.process(
        event=eth_gain_event,
        events_iterator=peekable([]),
    )
    assert consumed_num == 1


def test_accounting_no_settings(accounting_pot: 'AccountingPot'):
    """Test that if there are no settings provided, the event is not taken into account"""
    event = EvmEvent(
        tx_ref=EXAMPLE_EVM_HASH,
        sequence_index=0,
        timestamp=TimestampMS(0),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ZERO,
    )
    consumed_num = accounting_pot.events_accountant.process(
        event=event,
        events_iterator=peekable([]),
    )

    assert consumed_num == 1
    assert len(accounting_pot.pnls) == 0, 'Nothing should have happened since there were no settings'  # noqa: E501


@pytest.mark.parametrize(('event_type', 'event_subtype', 'is_taxable'), [
    (HistoryEventType.RECEIVE, HistoryEventSubType.NONE, True),
    (HistoryEventType.RECEIVE, HistoryEventSubType.AIRDROP, False),
    (HistoryEventType.RECEIVE, HistoryEventSubType.REWARD, True),
])
@pytest.mark.parametrize('mocked_price_queries', [MOCKED_PRICES])
# Check that accounting rules are applied no matter what event class is used
@pytest.mark.parametrize('entry_type', ['history_event', 'evm_event'])
def test_accounting_receive_settings(
        accounting_pot: 'AccountingPot',
        event_type: 'HistoryEventType',
        event_subtype: 'HistoryEventSubType',
        is_taxable: bool,
        entry_type: Literal['history_event', 'evm_event'],
):
    """Test that the default accounting settings for receiving are correct"""
    _gain_one_ether(
        events_accountant=accounting_pot.events_accountant,
        event_type=event_type,
        event_subtype=event_subtype,
        entry_type=entry_type,
    )
    expected_extra_data = {}
    if entry_type == 'evm_event':
        expected_extra_data = {'tx_ref': EXAMPLE_TX_HASH_HEX}

    expected_event = ProcessedAccountingEvent(
        event_type=AccountingEventType.TRANSACTION_EVENT,
        notes='Received 1 ETH',
        location=Location.ETHEREUM,
        timestamp=TIMESTAMP_1_SECS,
        asset=A_ETH,
        free_amount=ZERO if is_taxable else ONE,
        taxable_amount=ONE if is_taxable else ZERO,
        price=Price(ETH_PRICE_TS_1),
        pnl=PNL(
            taxable=ETH_PRICE_TS_1 if is_taxable else ZERO,
            free=ZERO,
        ),
        cost_basis=None,
        index=0,
        extra_data=expected_extra_data,
    )
    expected_event.count_entire_amount_spend = False
    expected_event.count_cost_basis_pnl = is_taxable

    assert accounting_pot.processed_events == [expected_event]
    assert accounting_pot.pnls.taxable == ETH_PRICE_TS_1 if is_taxable else ZERO
    assert accounting_pot.pnls.free == ZERO


@pytest.mark.parametrize(('event_type', 'event_subtype', 'notes', 'is_taxable', 'counterparty', 'gas_taxable', 'include_crypto2crypto'), [  # noqa: E501
    (HistoryEventType.SPEND, HistoryEventSubType.NONE, 'Send 0.5 ETH to 0xABC', True, None, False, False),  # noqa: E501
    (HistoryEventType.SPEND, HistoryEventSubType.FEE, 'Pay fee of 0.5 ETH', True, None, False, False),  # noqa: E501
    (HistoryEventType.SPEND, HistoryEventSubType.FEE, 'Burn 0.5 ETH for gas', True, CPT_GAS, True, False),  # noqa: E501
    (HistoryEventType.SPEND, HistoryEventSubType.FEE, 'Burn 0.5 ETH for gas', True, CPT_GAS, True, True),  # noqa: E501
    (HistoryEventType.SPEND, HistoryEventSubType.FEE, 'Burn 0.5 ETH for gas', False, CPT_GAS, False, False),  # noqa: E501
    (HistoryEventType.SPEND, HistoryEventSubType.FEE, 'Burn 0.5 ETH for gas', False, CPT_GAS, False, True),  # noqa: E501
])
@pytest.mark.parametrize('mocked_price_queries', [MOCKED_PRICES])
def test_accounting_spend_settings(
        accounting_pot: 'AccountingPot',
        event_type: 'HistoryEventType',
        event_subtype: 'HistoryEventSubType',
        notes: str,
        is_taxable: bool,
        counterparty: str | None,
        gas_taxable: bool,
        include_crypto2crypto,
):
    _gain_one_ether(events_accountant=accounting_pot.events_accountant)
    spend_event = EvmEvent(
        tx_ref=EXAMPLE_EVM_HASH,
        sequence_index=0,
        timestamp=TIMESTAMP_2_MS,
        location=Location.ETHEREUM,
        location_label=EXAMPLE_ADDRESS,
        asset=A_ETH,
        amount=FVal(0.5),
        notes=notes,
        event_type=event_type,
        event_subtype=event_subtype,
        counterparty=counterparty,
    )
    consumed_num = accounting_pot.events_accountant.process(
        event=spend_event,
        events_iterator=peekable([]),
    )
    assert consumed_num == 1

    acquisition_event = AssetAcquisitionEvent(
        amount=ONE,
        timestamp=TIMESTAMP_1_SECS,
        rate=Price(ETH_PRICE_TS_1),
        index=0,
    )
    acquisition_event.remaining_amount = FVal(0.5)
    cost_basis = None
    if is_taxable and (counterparty != CPT_GAS or include_crypto2crypto):
        cost_basis = CostBasisInfo(
            taxable_amount=FVal(0.5) if is_taxable else ZERO,
            taxable_bought_cost=ETH_PRICE_TS_1 / 2,
            taxfree_bought_cost=ZERO,
            matched_acquisitions=[
                MatchedAcquisition(
                    amount=FVal(0.5),
                    event=acquisition_event,
                    taxable=True,
                ),
            ],
            is_complete=True,
        )
    taxable_pnl = ZERO
    if is_taxable and (counterparty != CPT_GAS or include_crypto2crypto):
        taxable_pnl = -FVal(1000)
    elif is_taxable and counterparty == CPT_GAS and include_crypto2crypto is False:
        taxable_pnl = -FVal(1500)

    free_amount, taxable_amount = (FVal(0.5), ZERO) if counterparty == CPT_GAS and not gas_taxable else (ZERO, FVal(0.5))  # noqa: E501
    expected_event = ProcessedAccountingEvent(
        event_type=AccountingEventType.TRANSACTION_EVENT,
        notes=notes,
        location=Location.ETHEREUM,
        timestamp=TIMESTAMP_2_SECS,
        asset=A_ETH,
        free_amount=free_amount,
        taxable_amount=taxable_amount,
        price=Price(ETH_PRICE_TS_2),
        pnl=PNL(taxable=taxable_pnl, free=ZERO),
        cost_basis=cost_basis,
        index=1,
        extra_data={'tx_ref': EXAMPLE_TX_HASH_HEX},
    )
    expected_event.count_entire_amount_spend = is_taxable
    expected_event.count_cost_basis_pnl = is_taxable and (counterparty != CPT_GAS or include_crypto2crypto)  # noqa: E501
    assert accounting_pot.processed_events[-1] == expected_event
    assert accounting_pot.pnls.taxable == ETH_PRICE_TS_1 + expected_event.pnl.taxable
    assert accounting_pot.pnls.free == ZERO


@pytest.mark.parametrize('mocked_price_queries', [MOCKED_PRICES])
@pytest.mark.parametrize('counterparty', [None, 'nonexistent_counterparty'])
def test_accounting_swap_settings(accounting_pot: 'AccountingPot', counterparty: str):
    """
    Test that the default accounting settings for swaps are correct.
    Also checks that if counterparty is not known we fallback to default swaps treatment.
    """
    _gain_one_ether(events_accountant=accounting_pot.events_accountant)
    swap_spend_event = EvmEvent(
        tx_ref=EXAMPLE_EVM_HASH,
        sequence_index=1,
        timestamp=TIMESTAMP_2_MS,
        location=Location.ETHEREUM,
        location_label=EXAMPLE_ADDRESS,
        asset=A_ETH,
        amount=ONE,
        notes='Swap 1 ETH in a uniswap pool',
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        counterparty=counterparty,
    )
    swap_receive_event = EvmEvent(
        tx_ref=EXAMPLE_EVM_HASH,
        sequence_index=2,
        timestamp=TIMESTAMP_2_MS,
        location=Location.ETHEREUM,
        location_label=EXAMPLE_ADDRESS,
        asset=A_DAI,
        amount=FVal(3000),
        notes='Receive 3000 DAI as the result of a swap',
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        counterparty=counterparty,
    )
    consumed_num = accounting_pot.events_accountant.process(
        event=swap_spend_event,
        events_iterator=peekable([swap_receive_event]),
    )
    assert consumed_num == 2
    acquisition_event = AssetAcquisitionEvent(
        amount=ONE,
        timestamp=TIMESTAMP_1_SECS,
        rate=Price(ETH_PRICE_TS_1),
        index=0,
    )
    acquisition_event.remaining_amount = ZERO

    expected_spend_event = ProcessedAccountingEvent(
        event_type=AccountingEventType.TRANSACTION_EVENT,
        notes='Swap 1 ETH in a uniswap pool',
        location=Location.ETHEREUM,
        timestamp=TIMESTAMP_2_SECS,
        asset=A_ETH,
        free_amount=ZERO,
        taxable_amount=ONE,
        price=Price(FVal(3000)),
        pnl=PNL(free=ZERO, taxable=FVal(1000)),
        cost_basis=CostBasisInfo(
            taxable_amount=ONE,
            taxable_bought_cost=ETH_PRICE_TS_1,
            taxfree_bought_cost=ZERO,
            matched_acquisitions=[MatchedAcquisition(
                amount=ONE,
                event=acquisition_event,
                taxable=True,
            )],
            is_complete=True,
        ),
        index=1,
        extra_data={
            'tx_ref': EXAMPLE_TX_HASH_HEX,
            'group_id': f'{swap_spend_event.group_identifier}12',
        },
    )
    expected_spend_event.count_entire_amount_spend = False
    expected_spend_event.count_cost_basis_pnl = True

    expected_receive_event = ProcessedAccountingEvent(
        event_type=AccountingEventType.TRANSACTION_EVENT,
        notes='Receive 3000 DAI as the result of a swap',
        location=Location.ETHEREUM,
        timestamp=TIMESTAMP_2_SECS,
        asset=A_DAI,
        free_amount=FVal(3000),
        taxable_amount=ZERO,
        price=Price(ONE),
        pnl=PNL(free=ZERO, taxable=ZERO),
        cost_basis=None,
        index=2,
        extra_data={
            'tx_ref': EXAMPLE_TX_HASH_HEX,
            'group_id': f'{swap_receive_event.group_identifier}12',
        },
    )
    expected_receive_event.count_entire_amount_spend = False
    expected_receive_event.count_cost_basis_pnl = False
    assert accounting_pot.processed_events[1:] == [expected_spend_event, expected_receive_event]
    assert accounting_pot.pnls.taxable == ETH_PRICE_TS_1 + expected_spend_event.pnl.taxable


TIMESTAMP_3_SECS = Timestamp(1633593636)
TIMESTAMP_3_MS = ts_sec_to_ms(TIMESTAMP_3_SECS)
WETH_PRICE_TS_3 = FVal('4000')

MOCKED_PRICES_WITH_WETH = {
    'ETH': {
        'EUR': {
            TIMESTAMP_1_SECS: ETH_PRICE_TS_1,
            TIMESTAMP_2_SECS: ETH_PRICE_TS_2,
            TIMESTAMP_3_SECS: WETH_PRICE_TS_3,
        },
    },
    A_WETH.identifier: {
        'EUR': {
            TIMESTAMP_1_SECS: ETH_PRICE_TS_1,
            TIMESTAMP_2_SECS: ETH_PRICE_TS_2,
            TIMESTAMP_3_SECS: WETH_PRICE_TS_3,
        },
    },
    A_DAI.identifier: {
        'EUR': {
            TIMESTAMP_2_SECS: Price(ONE),
        },
    },
}


def _setup_basis_transfer_rules(accounting_pot: 'AccountingPot') -> None:
    """Insert basis_transfer rules for both WETH wrap and unwrap, then re-reset the pot."""
    rules_db = DBAccountingRules(accounting_pot.database)
    basis_transfer_rule = BaseEventSettings(
        taxable=False,
        count_entire_amount_spend=False,
        count_cost_basis_pnl=False,
        accounting_treatment=TxAccountingTreatment.BASIS_TRANSFER,
    )
    rules_db.add_accounting_rule(
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        counterparty=CPT_WETH,
        rule=basis_transfer_rule,
        links={},
        force_update=True,
    )
    rules_db.add_accounting_rule(
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        counterparty=CPT_WETH,
        rule=basis_transfer_rule,
        links={},
        force_update=True,
    )
    with accounting_pot.database.conn.read_ctx() as cursor:
        settings = accounting_pot.database.get_settings(cursor)
    accounting_pot.reset(
        settings=settings,
        start_ts=Timestamp(0),
        end_ts=Timestamp(0),
        report_id=1,
    )


@pytest.mark.parametrize('mocked_price_queries', [MOCKED_PRICES_WITH_WETH])
def test_accounting_basis_transfer_weth_wrap(accounting_pot: 'AccountingPot'):
    """
    Test the full ETH -> WETH wrap -> WETH sale scenario:
    1. Acquire 1 ETH at 2000 EUR (TIMESTAMP_1)
    2. Wrap ETH -> WETH (TIMESTAMP_2) — should be neutral, zero PnL
    3. Sell 1 WETH at 4000 EUR (TIMESTAMP_3) — should match original ETH basis of 2000
       yielding taxable PnL of 2000 EUR
    """
    _setup_basis_transfer_rules(accounting_pot)

    # Step 1: Acquire 1 ETH at TIMESTAMP_1 (price = 2000 EUR)
    _gain_one_ether(events_accountant=accounting_pot.events_accountant)
    assert len(accounting_pot.processed_events) == 1
    pnl_after_acquire = accounting_pot.pnls.taxable

    # Step 2: Wrap ETH -> WETH at TIMESTAMP_2
    wrap_out_event = EvmEvent(
        tx_ref=EXAMPLE_EVM_HASH,
        sequence_index=1,
        timestamp=TIMESTAMP_2_MS,
        location=Location.ETHEREUM,
        location_label=EXAMPLE_ADDRESS,
        asset=A_ETH,
        amount=ONE,
        notes='Wrap 1 ETH in WETH',
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        counterparty=CPT_WETH,
    )
    wrap_in_event = EvmEvent(
        tx_ref=EXAMPLE_EVM_HASH,
        sequence_index=2,
        timestamp=TIMESTAMP_2_MS,
        location=Location.ETHEREUM,
        location_label=EXAMPLE_ADDRESS,
        asset=A_WETH,
        amount=ONE,
        notes='Receive 1 WETH',
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        counterparty=CPT_WETH,
    )

    consumed_num = accounting_pot.events_accountant.process(
        event=wrap_out_event,
        events_iterator=peekable([wrap_in_event]),
    )
    assert consumed_num == 2
    assert len(accounting_pot.processed_events) == 1, 'Wrap should not add processed events'
    assert accounting_pot.pnls.taxable == pnl_after_acquire, 'Wrap should not change PnL'

    # Step 3: Sell 1 WETH at TIMESTAMP_3 (price = 4000 EUR)
    # Since WETH maps to the ETH cost basis pool, the acquisition lot at 2000 EUR should be used.
    weth_sell_event = EvmEvent(
        tx_ref=make_evm_tx_hash(),
        sequence_index=0,
        timestamp=TIMESTAMP_3_MS,
        location=Location.ETHEREUM,
        location_label=EXAMPLE_ADDRESS,
        asset=A_WETH,
        amount=ONE,
        notes='Send 1 WETH',
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
    )
    consumed_num = accounting_pot.events_accountant.process(
        event=weth_sell_event,
        events_iterator=peekable([]),
    )
    assert consumed_num == 1
    assert len(accounting_pot.processed_events) == 2

    # The WETH sell should use the original ETH acquisition basis of 2000 EUR.
    sell_event = accounting_pot.processed_events[-1]
    assert sell_event.cost_basis is not None, 'WETH sell should have matched cost basis'
    assert sell_event.cost_basis.taxable_bought_cost == ETH_PRICE_TS_1, (
        f'Expected original ETH basis of {ETH_PRICE_TS_1}, got {sell_event.cost_basis.taxable_bought_cost}'  # noqa: E501
    )
    assert sell_event.cost_basis.is_complete is True, 'Cost basis should be fully matched'
    # For a spend event pnl = sale_value - taxable_bought_cost.
    # With count_entire_amount_spend=True: pnl = -taxable_bought_cost = -ETH_PRICE_TS_1
    assert sell_event.pnl.taxable == -ETH_PRICE_TS_1


@pytest.mark.parametrize('mocked_price_queries', [MOCKED_PRICES])
def test_accounting_basis_transfer_missing_pair(accounting_pot: 'AccountingPot'):
    """Test that basis_transfer gracefully handles a missing paired event."""
    _setup_basis_transfer_rules(accounting_pot)

    wrap_out_event = EvmEvent(
        tx_ref=EXAMPLE_EVM_HASH,
        sequence_index=1,
        timestamp=TIMESTAMP_2_MS,
        location=Location.ETHEREUM,
        location_label=EXAMPLE_ADDRESS,
        asset=A_ETH,
        amount=ONE,
        notes='Wrap 1 ETH in WETH',
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        counterparty=CPT_WETH,
    )

    # No paired event in iterator - should return 1 (graceful fallback)
    consumed_num = accounting_pot.events_accountant.process(
        event=wrap_out_event,
        events_iterator=peekable([]),
    )
    assert consumed_num == 1


@pytest.mark.parametrize('use_basis_transfer', [True, False])
@pytest.mark.parametrize('mocked_price_queries', [MOCKED_PRICES_WITH_WETH])
def test_accounting_basis_transfer_weth_unwrap(accounting_pot: 'AccountingPot', use_basis_transfer: bool):  # noqa: E501
    """
    Test the full WETH acquire -> WETH unwrap -> ETH sale scenario:
    1. Acquire 1 WETH at 2000 EUR (TIMESTAMP_1)
    2. Unwrap WETH -> ETH (TIMESTAMP_2)
       - With BASIS_TRANSFER: both paired events consumed atomically, zero PnL
       - Without: default SPEND/RETURN_WRAPPED rule processes only the out-event
         (consumed_num=1), leaving the paired in-event for later processing if needed
    3. Sell 1 ETH at 4000 EUR (TIMESTAMP_3) — in both cases the original WETH basis
       of 2000 is used since WETH and ETH share the same cost-basis pool
    """
    if use_basis_transfer:
        _setup_basis_transfer_rules(accounting_pot)

    # Step 1: Acquire 1 WETH at TIMESTAMP_1 (price = 2000 EUR)
    weth_acquire_event = EvmEvent(
        tx_ref=EXAMPLE_EVM_HASH,
        sequence_index=0,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        location_label=EXAMPLE_ADDRESS,
        asset=A_WETH,
        amount=ONE,
        notes='Received 1 WETH',
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
    )
    consumed_num = accounting_pot.events_accountant.process(
        event=weth_acquire_event,
        events_iterator=peekable([]),
    )
    assert consumed_num == 1
    assert len(accounting_pot.processed_events) == 1
    pnl_after_acquire = accounting_pot.pnls.taxable

    # Step 2: Unwrap WETH -> ETH at TIMESTAMP_2
    unwrap_out_event = EvmEvent(
        tx_ref=(unwrap_hash := make_evm_tx_hash()),
        sequence_index=1,
        timestamp=TIMESTAMP_2_MS,
        location=Location.ETHEREUM,
        location_label=EXAMPLE_ADDRESS,
        asset=A_WETH,
        amount=ONE,
        notes='Unwrap 1 WETH',
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        counterparty=CPT_WETH,
    )
    unwrap_in_event = EvmEvent(
        tx_ref=unwrap_hash,
        sequence_index=2,
        timestamp=TIMESTAMP_2_MS,
        location=Location.ETHEREUM,
        location_label=EXAMPLE_ADDRESS,
        asset=A_ETH,
        amount=ONE,
        notes='Receive 1 ETH',
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        counterparty=CPT_WETH,
    )

    consumed_num = accounting_pot.events_accountant.process(
        event=unwrap_out_event,
        events_iterator=peekable([unwrap_in_event]),
    )
    if use_basis_transfer:
        # Both paired events consumed atomically; no processed events or PnL change
        assert consumed_num == 2
        assert len(accounting_pot.processed_events) == 1, 'Unwrap should not add processed events'
        assert accounting_pot.pnls.taxable == pnl_after_acquire, 'Unwrap should not change PnL'
    else:
        # Default rule (taxable=false, count_cost_basis_pnl=false): adds a non-taxable
        # processed event for the out-leg only. No cost basis is consumed and no PnL is realized.
        assert consumed_num == 1
        assert len(accounting_pot.processed_events) == 2, 'Default SPEND rule adds a processed event'  # noqa: E501
        assert accounting_pot.pnls.taxable == pnl_after_acquire, 'Non-taxable unwrap should not change PnL'    # noqa: E501
        unwrap_processed_event = accounting_pot.processed_events[-1]
        assert unwrap_processed_event.cost_basis is None
        assert unwrap_processed_event.taxable_amount == ZERO
        assert unwrap_processed_event.free_amount == ONE

    # Step 3: Sell 1 ETH at TIMESTAMP_3 (price = 4000 EUR)
    eth_sell_event = EvmEvent(
        tx_ref=make_evm_tx_hash(),
        sequence_index=0,
        timestamp=TIMESTAMP_3_MS,
        location=Location.ETHEREUM,
        location_label=EXAMPLE_ADDRESS,
        asset=A_ETH,
        amount=ONE,
        notes='Send 1 ETH',
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
    )
    consumed_num = accounting_pot.events_accountant.process(
        event=eth_sell_event,
        events_iterator=peekable([]),
    )
    assert consumed_num == 1
    sell_event = accounting_pot.processed_events[-1]
    assert sell_event.cost_basis is not None
    if use_basis_transfer:
        assert len(accounting_pot.processed_events) == 2
    else:
        assert len(accounting_pot.processed_events) == 3

    # In both cases, the ETH sell uses the original WETH acquisition basis of 2000 EUR.
    assert sell_event.cost_basis.taxable_bought_cost == ETH_PRICE_TS_1, (
        f'Expected original WETH basis of {ETH_PRICE_TS_1}, got {sell_event.cost_basis.taxable_bought_cost}'  # noqa: E501
    )
    assert sell_event.cost_basis.is_complete is True
    assert sell_event.pnl.taxable == -ETH_PRICE_TS_1


@pytest.mark.parametrize('use_basis_transfer', [True, False])
@pytest.mark.parametrize('mocked_price_queries', [MOCKED_PRICES_WITH_WETH])
def test_basis_transfer_vs_default_rules_weth_wrap(accounting_pot: 'AccountingPot', use_basis_transfer: bool):  # noqa: E501
    """
    Compare BASIS_TRANSFER vs default rules for ETH wrapping.

    With default rules the DEPOSIT/DEPOSIT_FOR_WRAPPED out-event calls spend_asset()
    with taxable_spend=false (since taxable=false but count_cost_basis_pnl=true),
    which silently consumes the original lot via reduce_asset_amount(). The in-event
    then creates a fresh lot at wrap-time price. Net effect: cost basis is reset.

    With BASIS_TRANSFER both events are consumed atomically and the pool is untouched,
    preserving the original acquisition cost.
    """
    if use_basis_transfer:
        _setup_basis_transfer_rules(accounting_pot)

    # Step 1: Acquire 1 ETH at TIMESTAMP_1 (price = 2000 EUR)
    _gain_one_ether(events_accountant=accounting_pot.events_accountant)
    assert len(accounting_pot.processed_events) == 1

    # Step 2: Wrap ETH -> WETH at TIMESTAMP_2 (price = 3000 EUR)
    wrap_out_event = EvmEvent(
        tx_ref=(wrap_hash := make_evm_tx_hash()),
        sequence_index=1,
        timestamp=TIMESTAMP_2_MS,
        location=Location.ETHEREUM,
        location_label=EXAMPLE_ADDRESS,
        asset=A_ETH,
        amount=ONE,
        notes='Wrap 1 ETH in WETH',
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        counterparty=CPT_WETH,
    )
    wrap_in_event = EvmEvent(
        tx_ref=wrap_hash,
        sequence_index=2,
        timestamp=TIMESTAMP_2_MS,
        location=Location.ETHEREUM,
        location_label=EXAMPLE_ADDRESS,
        asset=A_WETH,
        amount=ONE,
        notes='Receive 1 WETH',
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        counterparty=CPT_WETH,
    )

    if use_basis_transfer:
        consumed_num = accounting_pot.events_accountant.process(
            event=wrap_out_event,
            events_iterator=peekable([wrap_in_event]),
        )
        assert consumed_num == 2
        assert len(accounting_pot.processed_events) == 1
    else:
        # Real accounting run: both events processed separately
        consumed_num = accounting_pot.events_accountant.process(
            event=wrap_out_event,
            events_iterator=peekable([wrap_in_event]),
        )
        assert consumed_num == 1
        # The in-event was not consumed by the out-event, process it separately
        consumed_num = accounting_pot.events_accountant.process(
            event=wrap_in_event,
            events_iterator=peekable([]),
        )
        assert consumed_num == 1

    # Step 3: Sell 1 WETH at TIMESTAMP_3 (price = 4000 EUR)
    weth_sell_event = EvmEvent(
        tx_ref=make_evm_tx_hash(),
        sequence_index=0,
        timestamp=TIMESTAMP_3_MS,
        location=Location.ETHEREUM,
        location_label=EXAMPLE_ADDRESS,
        asset=A_WETH,
        amount=ONE,
        notes='Send 1 WETH',
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
    )
    consumed_num = accounting_pot.events_accountant.process(
        event=weth_sell_event,
        events_iterator=peekable([]),
    )
    assert consumed_num == 1

    sell_event = accounting_pot.processed_events[-1]
    assert sell_event.cost_basis is not None
    assert sell_event.cost_basis.is_complete is True

    if use_basis_transfer:
        # Original lot (2000) preserved → sell uses that basis
        assert sell_event.cost_basis.taxable_bought_cost == ETH_PRICE_TS_1
        assert sell_event.pnl.taxable == -ETH_PRICE_TS_1
    else:
        # Original lot consumed by the out-event, fresh lot created at 3000 by the in-event.
        # The sell matches the stepped-up basis instead of the original acquisition cost.
        assert sell_event.cost_basis.taxable_bought_cost == ETH_PRICE_TS_2
        assert sell_event.pnl.taxable == -ETH_PRICE_TS_2
