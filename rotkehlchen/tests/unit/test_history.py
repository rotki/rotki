import pytest

from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.eth2.structures import ValidatorDailyStats
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH, A_ETH2, A_USDC
from rotkehlchen.db.filtering import LedgerActionsFilterQuery
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.fval import FVal
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.tests.utils.accounting import accounting_history_process, check_pnls_and_csv
from rotkehlchen.tests.utils.history import prices
from rotkehlchen.tests.utils.messages import no_message_errors
from rotkehlchen.types import Location


def test_query_ledger_actions(events_historian, function_scope_messages_aggregator):
    """
    Create actions and query the events historian to check that the history
    has events previous to the selected from_ts. This allows us to verify that
    actions before one period are counted in the PnL report to calculate cost basis.
    https://github.com/rotki/rotki/issues/2541
    """

    selected_timestamp = 10
    db = DBLedgerActions(events_historian.db, function_scope_messages_aggregator)

    with events_historian.db.user_write() as cursor:
        action = LedgerAction(
            identifier=0,  # whatever
            timestamp=selected_timestamp - 2,
            action_type=LedgerActionType.INCOME,
            location=Location.EXTERNAL,
            amount=ONE,
            asset=A_ETH,
            rate=None,
            rate_asset=None,
            link=None,
            notes=None,
        )
        db.add_ledger_action(cursor, action)

        action = LedgerAction(
            identifier=0,  # whatever
            timestamp=selected_timestamp + 3,
            action_type=LedgerActionType.EXPENSE,
            location=Location.EXTERNAL,
            amount=FVal(0.5),
            asset=A_ETH,
            rate=None,
            rate_asset=None,
            link=None,
            notes=None,
        )
        db.add_ledger_action(cursor, action)

        action = LedgerAction(
            identifier=0,  # whatever
            timestamp=selected_timestamp + 5,
            action_type=LedgerActionType.INCOME,
            location=Location.EXTERNAL,
            amount=FVal(10),
            asset=A_USDC,
            rate=None,
            rate_asset=None,
            link=None,
            notes=None,
        )
        db.add_ledger_action(cursor, action)

        actions, length = events_historian.query_ledger_actions(
            filter_query=LedgerActionsFilterQuery.make(to_ts=selected_timestamp + 4),
            only_cache=False,
        )

    assert any((action.timestamp < selected_timestamp for action in actions))
    assert length == 2


@pytest.mark.parametrize('value,result', [
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
            start_amount=FVal('32'),
            end_amount=FVal('32.05'),
            pnl=FVal('0.05'),  # 0.05 * 449.68 = 22.484
        ), ValidatorDailyStats(
            validator_index=1,
            timestamp=1607814000,  # ETH price: 469.82 ETH/EUR
            start_amount=FVal('32.05'),
            end_amount=FVal('32.045'),
            pnl=FVal('-0.005'),  # -0.005 * 469.82 + 0.005 * 469.82 - 0.005*449.68 = -2.2484
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier('XXX'),
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
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier('XXX'),
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
