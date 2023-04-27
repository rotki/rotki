import pytest

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.eth2.structures import ValidatorDailyStats
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH2
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.accounting import accounting_history_process, check_pnls_and_csv
from rotkehlchen.tests.utils.history import prices
from rotkehlchen.tests.utils.messages import no_message_errors
from rotkehlchen.types import Location


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_kraken_staking_events(accountant, google_service):
    """
    Test that staking events from kraken are correctly processed
    """
    history = [
        HistoryEvent(
            event_identifier=b'XXX',
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
        ), HistoryEvent(
            event_identifier=b'YYY',
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
    check_pnls_and_csv(accountant, expected_pnls, google_service)
    assert len(events) == 2
    expected_pnls = [FVal('0.25114638241'), FVal('0.22035944359')]
    for idx, event in enumerate(events):
        assert event.pnl.taxable == expected_pnls[idx]
        assert event.type == AccountingEventType.STAKING


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_eth2_staking(accountant, google_service):
    """Test that ethereum 2 staking is accounted for properly"""
    history = [
        ValidatorDailyStats(
            validator_index=1,
            timestamp=1607727600,  # ETH price: 449.68 ETH/EUR
            pnl=FVal('0.05'),  # 0.05 * 449.68 = 22.484
        ), ValidatorDailyStats(
            validator_index=1,
            timestamp=1607814000,  # ETH price: 469.82 ETH/EUR
            pnl=FVal('-0.005'),  # -0.005 * 469.82 + 0.005 * 469.82 - 0.005*449.68 = -2.2484
        ), ValidatorDailyStats(
            validator_index=1,
            timestamp=1607900400,  # ETH price: 486.57 ETH/EUR
            pnl=FVal('0.04'),  # 0.04 * 486.57 = 19.4628
        ), ValidatorDailyStats(
            validator_index=2,
            timestamp=1607900400,
            pnl=FVal('0.045'),  # 0.045 * 486.57 = 21.89565
        ),
    ]

    accounting_history_process(
        accountant,
        start_ts=1606727600,
        end_ts=1640493376,
        history_list=history,
    )
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({  # 22.484 - 2.2484 + 19.4628 + 21.89565
        AccountingEventType.STAKING: PNL(taxable=FVal('61.59405'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)
