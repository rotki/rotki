"""This file should probably be split into basic & per protocol accounting test files if too big"""

import pytest

from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.accounting import accounting_history_process, check_pnls_and_csv
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.tests.utils.history import prices
from rotkehlchen.tests.utils.messages import no_message_errors
from rotkehlchen.types import Location, Timestamp


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_receiving_value_from_tx(accountant, google_service):
    """
    Test that receiving a transaction that provides value works fine
    """
    addr2 = make_ethereum_address()
    tx_hash = HistoryBaseEntry.deserialize_event_identifier('0x5cc0e6e62753551313412492296d5e57bea0a9d1ce507cc96aa4aa076c5bde7a')  # noqa: E501
    history = [
        HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=1569924574000,
            location=Location.BLOCKCHAIN,
            location_label=make_ethereum_address(),
            asset=A_ETH,
            balance=Balance(amount=FVal('1.5')),
            notes=f'Received 1.5 ETH from {addr2}',
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            counterparty=addr2,
        )]
    accounting_history_process(
        accountant,
        start_ts=0,
        end_ts=1640493376,
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
    tx_hash = HistoryBaseEntry.deserialize_event_identifier('0x5cc0e6e62753551313412492296d5e57bea0a9d1ce507cc96aa4aa076c5bde7a')  # noqa: E501
    history = [
        LedgerAction(
            identifier=0,
            timestamp=Timestamp(1539713238),  # 178.615 EUR/ETH
            action_type=LedgerActionType.GIFT,  # gift so not counting as income
            location=Location.KRAKEN,
            amount=ONE,
            asset=A_ETH,
            rate=None,
            rate_asset=None,
            link=None,
            notes='',
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=1640493374000,  # 4072.51 EUR/ETH
            location=Location.BLOCKCHAIN,
            location_label=make_ethereum_address(),
            asset=A_ETH,
            balance=Balance(amount=FVal('0.01')),
            notes='Burned 0.01 ETH for gas',
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            counterparty=CPT_GAS,
        )]
    accounting_history_process(
        accountant,
        start_ts=0,
        end_ts=1640493376,
        history_list=history,
    )
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({
        AccountingEventType.TRANSACTION_EVENT: PNL(
            taxable=FVal('-40.7251'),
            free=FVal('38.93895')),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)
