import pytest

from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH, A_USDC
from rotkehlchen.db.filtering import LedgerActionsFilterQuery
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.fval import FVal
from rotkehlchen.history.types import HistoricalPriceOracle
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
    db.add_ledger_action(action)

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
    db.add_ledger_action(action)

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
    db.add_ledger_action(action)

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
