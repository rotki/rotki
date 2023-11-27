import pytest

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.modules.eth2.structures import ValidatorDailyStats
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_ETH2
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.tests.utils.accounting import accounting_history_process, check_pnls_and_csv
from rotkehlchen.tests.utils.history import prices
from rotkehlchen.tests.utils.messages import no_message_errors
from rotkehlchen.types import Location


@pytest.mark.parametrize(('value', 'result'), [
    ('manual', HistoricalPriceOracle.MANUAL),
    ('coingecko', HistoricalPriceOracle.COINGECKO),
    ('cryptocompare', HistoricalPriceOracle.CRYPTOCOMPARE),
    ('xratescom', HistoricalPriceOracle.XRATESCOM),
])
def test_historical_price_oracle_deserialize(value, result):
    assert HistoricalPriceOracle.deserialize(value) == result


@pytest.mark.parametrize('db_settings', [
    {'eth_staking_taxable_after_withdrawal_enabled': False},
    {'eth_staking_taxable_after_withdrawal_enabled': True},
])
@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_pnl_processing_with_eth2_staking_setting(accountant, db_settings):
    """Test that toggling `eth_staking_taxable_after_withdrawal_enabled` setting produces
    the desired output.
    True -> ETH2 staking will not be taxed until withdrawal.
    False -> ETH2 staking daily reward is taxed as income. Default behaviour.
    """
    history = [
        ValidatorDailyStats(
            validator_index=1,
            timestamp=1607727600,  # ETH price: 449.68 ETH/EUR
            pnl=FVal('0.05'),  # 0.05 * 449.68 = 22.484
        ), ValidatorDailyStats(
            validator_index=1,
            timestamp=1607814000,  # ETH price: 469.82 ETH/EUR
            pnl=FVal('-0.005'),  # -0.005 * 469.82 + 0.005 * 469.82 - 0.005*449.68 = -2.2484
        ), HistoryEvent(
            event_identifier='XXX',
            sequence_index=0,
            timestamp=1625001464000,  # ETH price: 1837.31 ETH/EUR
            location=Location.KRAKEN,
            location_label='Kraken 1',
            asset=A_ETH2,
            balance=Balance(
                amount=FVal(0.0000541090),
                usd_value=FVal(0.212353475950),
            ),
            notes=None,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,  # 0.0000541090 * 1837.31 = 0.09941500679
        ), HistoryEvent(
            event_identifier='XXX',
            sequence_index=0,
            timestamp=1640493374000,  # ETH price: 4072.51 ETH/EUR
            location=Location.KRAKEN,
            location_label='Kraken 1',
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.0000541090),
                usd_value=FVal(0.212353475950),
            ),
            notes=None,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,  # 0.0000541090 * 4072.51 = 0.22035944359
        ),
    ]
    accounting_history_process(
        accountant,
        start_ts=1606727600,
        end_ts=1640493376,
        history_list=history,
    )
    no_message_errors(accountant.msg_aggregator)
    if db_settings['eth_staking_taxable_after_withdrawal_enabled'] is True:
        expected_pnls = PnlTotals({
            AccountingEventType.STAKING: PNL(taxable=FVal('0.22035944359'), free=ZERO),
        })
    else:
        expected_pnls = PnlTotals({  # 22.484 - 2.2484 + 0.09941500679 + 0.22035944359
            AccountingEventType.STAKING: PNL(taxable=FVal('20.55537445038'), free=ZERO),
        })
    check_pnls_and_csv(accountant, expected_pnls, None)
