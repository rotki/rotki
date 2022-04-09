"""This file should probably be split into basic & per protocol accounting test files if too big"""

import pytest

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.accounting.structures import (
    Balance,
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.accounting import accounting_history_process, check_pnls_and_csv
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.tests.utils.history import prices
from rotkehlchen.tests.utils.messages import no_message_errors
from rotkehlchen.types import Location


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_receiving_value_from_tx(accountant):
    """
    Test that receiving a transaction that provides value works fine
    """
    addr2 = make_ethereum_address()
    tx_hash = '0x5cc0e6e62753551313412492296d5e57bea0a9d1ce507cc96aa4aa076c5bde7a'
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
    check_pnls_and_csv(accountant, expected_pnls)
