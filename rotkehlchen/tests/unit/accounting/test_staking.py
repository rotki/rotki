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
from rotkehlchen.constants.assets import A_ETH2
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.accounting import accounting_history_process, check_pnls_and_csv
from rotkehlchen.tests.utils.history import prices
from rotkehlchen.tests.utils.messages import no_message_errors
from rotkehlchen.types import Location


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_kraken_staking_events(accountant):
    """
    Test that staking events from kraken are correctly processed
    """
    history = [
        HistoryBaseEntry(
            event_identifier='XXX',
            sequence_index=0,
            timestamp=1640493374000,
            location=Location.KRAKEN,
            location_label='Kraken 1',
            asset=A_ETH2,
            balance=Balance(
                amount=FVal(0.0000541090),
                usd_value=FVal(0.212353475950),
            ),
            notes=None,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
        ), HistoryBaseEntry(
            event_identifier='YYY',
            sequence_index=0,
            timestamp=1636638550000,
            location=Location.KRAKEN,
            location_label='Kraken 1',
            asset=A_ETH2,
            balance=Balance(
                amount=FVal(0.0000541090),
                usd_value=FVal(0.212353475950),
            ),
            notes=None,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
        )]
    _, events = accounting_history_process(
        accountant,
        start_ts=1636638549,
        end_ts=1640493376,
        history_list=history,
    )
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({
        AccountingEventType.STAKING: PNL(taxable=FVal('0.471505826'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls)
    assert len(events) == 2
    expected_pnls = [FVal('0.25114638241'), FVal('0.22035944359')]
    for idx, event in enumerate(events):
        assert event.pnl.taxable == expected_pnls[idx]
        assert event.type == AccountingEventType.STAKING
