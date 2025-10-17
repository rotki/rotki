"""This file should probably be split into basic & per protocol accounting test files if too big"""

import pytest

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.accounting import accounting_history_process, check_pnls_and_csv
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.history import prices
from rotkehlchen.tests.utils.messages import no_message_errors
from rotkehlchen.types import Location, Timestamp, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_receiving_value_from_tx(accountant, google_service):
    """
    Test that receiving a transaction that provides value works fine
    """
    addr2 = make_evm_address()
    tx_hash = deserialize_evm_tx_hash('0x5cc0e6e62753551313412492296d5e57bea0a9d1ce507cc96aa4aa076c5bde7a')  # noqa: E501
    history = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=Timestamp(1569924574000),
            location=Location.ETHEREUM,
            location_label=make_evm_address(),
            asset=A_ETH,
            amount=FVal('1.5'),
            notes=f'Received 1.5 ETH from {addr2}',
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            address=addr2,
        )]
    accounting_history_process(
        accountant,
        start_ts=Timestamp(0),
        end_ts=Timestamp(1640493376),
        history_list=history,
    )
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({
        AccountingEventType.TRANSACTION_EVENT: PNL(taxable=FVal('242.385'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_gas_fees_after_year(accountant, google_service):
    """
    Test that for an expense like gas fees after year the "selling" part is tax free
    PnL, and the expense part is taxable pnl.
    """
    tx_hash = deserialize_evm_tx_hash('0x5cc0e6e62753551313412492296d5e57bea0a9d1ce507cc96aa4aa076c5bde7a')  # noqa: E501
    history = [
        HistoryEvent(
            event_identifier='1',
            sequence_index=0,
            timestamp=TimestampMS(1539713238000),  # 178.615 EUR/ETH
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,  # not counting as income by default
            asset=A_ETH,
            amount=ONE,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1640493374000),  # 4072.51 EUR/ETH
            location=Location.ETHEREUM,
            location_label=make_evm_address(),
            asset=A_ETH,
            amount=FVal('0.01'),
            notes='Burn 0.01 ETH for gas',
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            counterparty=CPT_GAS,
        )]
    accounting_history_process(
        accountant,
        start_ts=Timestamp(0),
        end_ts=Timestamp(1640493376),
        history_list=history,
    )
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({
        AccountingEventType.TRANSACTION_EVENT: PNL(
            taxable=FVal('-40.7251'),
            free=FVal('38.93895')),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_ignoring_transaction_from_accounting(accountant, google_service, database):
    """
    Test that ignoring a transaction from accounting does not include it in the PnL

    2 events, same tx hash, one is optimism, the other Ethereum. (super improbable to happen)
    But just to test that chain is taken into account during ignoring
    """
    addr2 = make_evm_address()
    tx_hash = deserialize_evm_tx_hash('0x5cc0e6e62753551313412492296d5e57bea0a9d1ce507cc96aa4aa076c5bde7a')  # noqa: E501
    history = [
        EvmEvent(
            identifier=1,
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1569924574000),
            location=Location.OPTIMISM,
            location_label=make_evm_address(),
            asset=A_ETH,
            amount=FVal('1.5'),
            notes=f'Received 1.5 ETH from {addr2} in Optimism',
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            address=addr2,
        ), EvmEvent(
            identifier=2,
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1569924574000),
            location=Location.ETHEREUM,
            location_label=make_evm_address(),
            asset=A_ETH,
            amount=FVal('1.5'),
            notes=f'Received 1.5 ETH from {addr2} in Ethereum',
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            address=addr2,
        )]
    with database.user_write() as write_cursor:
        database.add_to_ignored_action_ids(
            write_cursor=write_cursor,
            identifiers=['10' + tx_hash.hex()],  # pylint: disable=no-member
        )
    events = accounting_history_process(
        accountant,
        start_ts=Timestamp(0),
        end_ts=Timestamp(1640493376),
        history_list=history,
    )
    assert len(events) == 2
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({
        AccountingEventType.TRANSACTION_EVENT: PNL(taxable=FVal('242.385'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)
