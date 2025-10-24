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
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_DAI, A_ETH
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
EXAMPLE_TX_HASH_HEX = EXAMPLE_EVM_HASH.hex()  # pylint: disable=no-member  # EvmTxHash does have hex() member
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
        kwargs = {'event_identifier': f'rotki_events_{EXAMPLE_EVM_HASH.hex()}'}  # pylint: disable=no-member
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
            'group_id': f'{swap_spend_event.event_identifier}12',
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
            'group_id': f'{swap_receive_event.event_identifier}12',
        },
    )
    expected_receive_event.count_entire_amount_spend = False
    expected_receive_event.count_cost_basis_pnl = False
    assert accounting_pot.processed_events[1:] == [expected_spend_event, expected_receive_event]
    assert accounting_pot.pnls.taxable == ETH_PRICE_TS_1 + expected_spend_event.pnl.taxable
