import pytest

from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_USDC
from rotkehlchen.db.filtering import LedgerActionsFilterQuery
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.history.events import limit_trade_list_to_period
from rotkehlchen.history.typing import HistoricalPriceOracle
from rotkehlchen.typing import Location, TradeType


def test_limit_trade_list_to_period():
    trade1 = Trade(
        timestamp=1459427707,
        location=Location.KRAKEN,
        base_asset=A_ETH,
        quote_asset=A_BTC,
        trade_type=TradeType.BUY,
        amount=FVal(1),
        rate=FVal(1),
        fee=FVal('0.1'),
        fee_currency=A_ETH,
        link='id1',
    )
    trade2 = Trade(
        timestamp=1469427707,
        location=Location.POLONIEX,
        base_asset=A_ETH,
        quote_asset=A_BTC,
        trade_type=TradeType.BUY,
        amount=FVal(1),
        rate=FVal(1),
        fee=FVal('0.1'),
        fee_currency=A_ETH,
        link='id2',
    )
    trade3 = Trade(
        timestamp=1479427707,
        location=Location.POLONIEX,
        base_asset=A_ETH,
        quote_asset=A_BTC,
        trade_type=TradeType.BUY,
        amount=FVal(1),
        rate=FVal(1),
        fee=FVal('0.1'),
        fee_currency=A_ETH,
        link='id3',
    )

    full_list = [trade1, trade2, trade3]
    assert limit_trade_list_to_period(full_list, 1459427706, 1479427708) == full_list
    assert limit_trade_list_to_period(full_list, 1459427707, 1479427708) == full_list
    assert limit_trade_list_to_period(full_list, 1459427707, 1479427707) == full_list

    expected = [trade2, trade3]
    assert limit_trade_list_to_period(full_list, 1459427708, 1479427707) == expected
    expected = [trade2]
    assert limit_trade_list_to_period(full_list, 1459427708, 1479427706) == expected
    assert limit_trade_list_to_period(full_list, 0, 10) == []
    assert limit_trade_list_to_period(full_list, 1479427708, 1479427719) == []
    assert limit_trade_list_to_period([trade1], 1459427707, 1459427707) == [trade1]
    assert limit_trade_list_to_period([trade2], 1469427707, 1469427707) == [trade2]
    assert limit_trade_list_to_period([trade3], 1479427707, 1479427707) == [trade3]
    assert limit_trade_list_to_period(full_list, 1459427707, 1459427707) == [trade1]
    assert limit_trade_list_to_period(full_list, 1469427707, 1469427707) == [trade2]
    assert limit_trade_list_to_period(full_list, 1479427707, 1479427707) == [trade3]


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
        amount=FVal(1),
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
