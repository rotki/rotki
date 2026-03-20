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
from rotkehlchen.assets.asset import Asset
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


# --- BASIS_TRANSFER tests ---

TIMESTAMP_3_SECS = Timestamp(1633593636)
TIMESTAMP_3_MS = ts_sec_to_ms(TIMESTAMP_3_SECS)
WETH_PRICE_TS_3 = FVal('4000')

# Aave v1 aDAI — not in any asset collection with DAI, so separate cost basis bucket
A_ADAI_V1 = Asset('eip155:1/erc20:0xfC1E690f61EFd961294b3e1Ce3313fBD8aa4f85d')

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
            TIMESTAMP_1_SECS: Price(ONE),
            TIMESTAMP_2_SECS: Price(ONE),
            TIMESTAMP_3_SECS: Price(ONE),
        },
    },
    A_ADAI_V1.identifier: {
        'EUR': {
            TIMESTAMP_1_SECS: Price(ONE),
            TIMESTAMP_2_SECS: Price(ONE),
            TIMESTAMP_3_SECS: Price(ONE),
        },
    },
}


def _setup_basis_transfer_rules(
        accounting_pot: 'AccountingPot',
        counterparty: str = CPT_WETH,
) -> None:
    """Insert basis_transfer rules for both wrap and unwrap, then re-reset the pot."""
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
        counterparty=counterparty,
        rule=basis_transfer_rule,
        links={},
        force_update=True,
    )
    rules_db.add_accounting_rule(
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        counterparty=counterparty,
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
def test_basis_transfer_weth_wrap(accounting_pot: 'AccountingPot'):
    """
    Test that BASIS_TRANSFER preserves cost basis across ETH → WETH wrapping.
    1. Acquire 1 ETH at 2000 EUR
    2. Wrap ETH → WETH (should be a no-op for cost basis since same bucket)
    3. Sell 1 WETH at 4000 EUR → cost basis should be original 2000 EUR
    """
    _setup_basis_transfer_rules(accounting_pot)

    # Step 1: Acquire 1 ETH at 2000 EUR
    _gain_one_ether(events_accountant=accounting_pot.events_accountant)
    assert len(accounting_pot.processed_events) == 1
    pnl_after_acquire = accounting_pot.pnls.taxable

    # Step 2: Wrap ETH → WETH
    wrap_out = EvmEvent(
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
    wrap_in = EvmEvent(
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

    assert (consumed := accounting_pot.events_accountant.process(
        event=wrap_out,
        events_iterator=peekable([wrap_in]),
    )) == 2, f'Expected 2 events consumed, got {consumed}'
    assert len(accounting_pot.processed_events) == 1, 'Wrap should not add processed events'
    assert accounting_pot.pnls.taxable == pnl_after_acquire, 'Wrap should not change PnL'

    # Step 3: Sell 1 WETH at 4000 EUR
    sell = EvmEvent(
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
    accounting_pot.events_accountant.process(
        event=sell,
        events_iterator=peekable([]),
    )

    sell_event = accounting_pot.processed_events[-1]
    assert sell_event.cost_basis is not None, 'WETH sell should have matched cost basis'
    assert sell_event.cost_basis.taxable_bought_cost == ETH_PRICE_TS_1, (
        f'Expected original ETH basis of {ETH_PRICE_TS_1}, '
        f'got {sell_event.cost_basis.taxable_bought_cost}'
    )
    assert sell_event.cost_basis.is_complete is True


@pytest.mark.parametrize('mocked_price_queries', [MOCKED_PRICES_WITH_WETH])
def test_basis_transfer_weth_unwrap(accounting_pot: 'AccountingPot'):
    """
    Test that BASIS_TRANSFER preserves cost basis across WETH → ETH unwrapping.
    1. Acquire 1 WETH at 2000 EUR
    2. Unwrap WETH → ETH (no-op for same-bucket cost basis)
    3. Sell 1 ETH at 4000 EUR → cost basis should be original 2000 EUR
    """
    _setup_basis_transfer_rules(accounting_pot)

    # Step 1: Acquire 1 WETH at 2000 EUR
    weth_acquire = EvmEvent(
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
    accounting_pot.events_accountant.process(
        event=weth_acquire,
        events_iterator=peekable([]),
    )
    pnl_after_acquire = accounting_pot.pnls.taxable

    # Step 2: Unwrap WETH → ETH
    unwrap_out = EvmEvent(
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
    unwrap_in = EvmEvent(
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

    assert accounting_pot.events_accountant.process(
        event=unwrap_out,
        events_iterator=peekable([unwrap_in]),
    ) == 2
    assert accounting_pot.pnls.taxable == pnl_after_acquire, 'Unwrap should not change PnL'

    # Step 3: Sell 1 ETH at 4000 EUR
    sell = EvmEvent(
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
    accounting_pot.events_accountant.process(
        event=sell,
        events_iterator=peekable([]),
    )

    sell_event = accounting_pot.processed_events[-1]
    assert sell_event.cost_basis is not None
    assert sell_event.cost_basis.taxable_bought_cost == ETH_PRICE_TS_1
    assert sell_event.cost_basis.is_complete is True


@pytest.mark.parametrize('mocked_price_queries', [MOCKED_PRICES_WITH_WETH])
def test_basis_transfer_different_bucket(accounting_pot: 'AccountingPot'):
    """
    Test that BASIS_TRANSFER correctly moves cost basis lots between assets
    in DIFFERENT cost basis buckets: DAI → aDAI (Aave v1 deposit).

    DAI and aDAI are separate assets with no shared collection, so the transfer
    must actually extract lots from DAI's bucket and re-insert them into aDAI's bucket
    with original acquisition prices preserved.
    """
    cpt_test = 'test_protocol'
    _setup_basis_transfer_rules(accounting_pot, counterparty=cpt_test)

    # Step 1: Acquire 100 DAI at 1 EUR each
    dai_acquire = EvmEvent(
        tx_ref=EXAMPLE_EVM_HASH,
        sequence_index=0,
        timestamp=TIMESTAMP_1_MS,
        location=Location.ETHEREUM,
        location_label=EXAMPLE_ADDRESS,
        asset=A_DAI,
        amount=FVal(100),
        notes='Received 100 DAI',
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
    )
    accounting_pot.events_accountant.process(
        event=dai_acquire,
        events_iterator=peekable([]),
    )

    # Verify DAI lot exists in cost basis
    dai_events = accounting_pot.cost_basis.get_events(A_DAI)
    assert len(dai_events.acquisitions_manager) == 1
    dai_acquisitions = dai_events.acquisitions_manager.get_acquisitions()
    assert dai_acquisitions[0].remaining_amount == FVal(100)
    assert dai_acquisitions[0].rate == Price(ONE)

    # Step 2: Deposit 100 DAI into Aave → receive 100 aDAI (1:1 for Aave v1)
    deposit_out = EvmEvent(
        tx_ref=(dep_hash := make_evm_tx_hash()),
        sequence_index=1,
        timestamp=TIMESTAMP_2_MS,
        location=Location.ETHEREUM,
        location_label=EXAMPLE_ADDRESS,
        asset=A_DAI,
        amount=FVal(100),
        notes='Deposit 100 DAI into Aave',
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        counterparty=cpt_test,
    )
    deposit_in = EvmEvent(
        tx_ref=dep_hash,
        sequence_index=2,
        timestamp=TIMESTAMP_2_MS,
        location=Location.ETHEREUM,
        location_label=EXAMPLE_ADDRESS,
        asset=A_ADAI_V1,
        amount=FVal(100),
        notes='Receive 100 aDAI from Aave',
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        counterparty=cpt_test,
    )

    assert accounting_pot.events_accountant.process(
        event=deposit_out,
        events_iterator=peekable([deposit_in]),
    ) == 2

    # Verify DAI lots are consumed (empty)
    assert len(dai_events.acquisitions_manager) == 0, 'DAI lots should be consumed by transfer'

    # Verify aDAI now has the transferred lot with preserved rate
    # Original: 100 DAI at 1 EUR each → total cost 100 EUR
    # Transferred: 100 aDAI at 1 EUR each (1:1 ratio, rate unchanged)
    # Total cost preserved: 100 * 1 = 100 EUR ✓
    adai_events = accounting_pot.cost_basis.get_events(A_ADAI_V1)
    adai_acquisitions = adai_events.acquisitions_manager.get_acquisitions()
    assert len(adai_acquisitions) == 1
    assert adai_acquisitions[0].remaining_amount == FVal(100)
    assert adai_acquisitions[0].rate == Price(ONE), (
        f'Expected transferred rate of 1 EUR, got {adai_acquisitions[0].rate}'
    )
    # Original acquisition timestamp is preserved, not the deposit timestamp
    assert adai_acquisitions[0].timestamp == TIMESTAMP_1_SECS


@pytest.mark.parametrize('mocked_price_queries', [MOCKED_PRICES])
def test_basis_transfer_missing_pair(accounting_pot: 'AccountingPot'):
    """Test that basis_transfer gracefully handles a missing paired event."""
    _setup_basis_transfer_rules(accounting_pot)

    wrap_out = EvmEvent(
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

    # No paired event → should return 1 (graceful fallback)
    assert accounting_pot.events_accountant.process(
        event=wrap_out,
        events_iterator=peekable([]),
    ) == 1


@pytest.mark.parametrize('mocked_price_queries', [MOCKED_PRICES_WITH_WETH])
def test_basis_transfer_vs_default_rules(accounting_pot: 'AccountingPot'):
    """
    Demonstrate that WITHOUT basis_transfer, the default rules reset cost basis
    on wrapping. The deposit out-event calls spend_asset() which consumes the
    original lot, and the receive in-event creates a fresh lot at wrap-time price.

    This test documents the bug that BASIS_TRANSFER fixes.
    """
    # Do NOT set up basis_transfer rules — use defaults

    # Step 1: Acquire 1 ETH at 2000 EUR
    _gain_one_ether(events_accountant=accounting_pot.events_accountant)

    # Step 2: Wrap ETH → WETH at timestamp 2 (price = 3000 EUR)
    # With default rules, both events are processed individually
    wrap_out = EvmEvent(
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
    wrap_in = EvmEvent(
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

    # Out event consumed separately (returns 1, not 2)
    consumed = accounting_pot.events_accountant.process(
        event=wrap_out,
        events_iterator=peekable([wrap_in]),
    )
    assert consumed == 1, 'Without BASIS_TRANSFER, out-event is processed alone'
    # In event also processed separately
    accounting_pot.events_accountant.process(
        event=wrap_in,
        events_iterator=peekable([]),
    )

    # Step 3: Sell 1 WETH at 4000 EUR
    sell = EvmEvent(
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
    accounting_pot.events_accountant.process(
        event=sell,
        events_iterator=peekable([]),
    )

    sell_event = accounting_pot.processed_events[-1]
    assert sell_event.cost_basis is not None
    # BUG: Without BASIS_TRANSFER, cost basis was reset to wrap-time price (3000)
    # instead of the original purchase price (2000)
    assert sell_event.cost_basis.taxable_bought_cost == ETH_PRICE_TS_2, (
        'Without BASIS_TRANSFER, cost basis is incorrectly reset to wrap-time price'
    )
