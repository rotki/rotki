from collections import defaultdict
from threading import Semaphore
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.api.websockets.typedefs import HistoryEventsStep
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_USDC
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.exchange import ExchangeWithoutApiSecret, HistoryEventQueue
from rotkehlchen.fval import FVal
from rotkehlchen.types import Location, Price, Timestamp


def test_history_event_queue_discards_failed_batch() -> None:
    database = MagicMock()
    event_queue = HistoryEventQueue(
        database=database,
        location_string='test',
        query_start_ts=Timestamp(0),
        events=[MagicMock()],
    )
    with (
        patch.object(
            DBHistoryEvents,
            'add_history_events',
            side_effect=DeserializationError('Failed to deserialize event'),
        ),
        pytest.raises(DeserializationError),
    ):
        event_queue.flush()

    assert event_queue.events == []


def test_history_event_queue_does_not_move_range_backwards() -> None:
    database = MagicMock()
    event_queue = HistoryEventQueue(
        database=database,
        location_string='test',
        query_start_ts=Timestamp(10),
    )

    with patch.object(DBQueryRanges, 'update_used_query_range') as update_range:
        event_queue.flush(queried_until_ts=Timestamp(9))
        assert event_queue.query_start_ts == Timestamp(10)
        update_range.assert_not_called()

        event_queue.flush(queried_until_ts=Timestamp(11))

    update_range.assert_called_once_with(
        write_cursor=database.user_write.return_value.__enter__.return_value,
        location_string='test',
        queried_ranges=[(Timestamp(10), Timestamp(11))],
    )
    assert event_queue.query_start_ts == Timestamp(11)


@pytest.mark.parametrize('error', [
    RemoteError('query failed'),
    DeserializationError('query failed'),
])
def test_history_query_flushes_and_finishes_on_error(
        error: RemoteError | DeserializationError,
) -> None:
    exchange = MagicMock()
    exchange.db = MagicMock()
    exchange.location = Location.BINANCE
    exchange.name = 'test'
    exchange.query_locks_map = defaultdict(Semaphore)
    exchange.query_locks_map_lock = Semaphore()
    exchange.query_online_history_events_into_queue.side_effect = error
    event_queue = MagicMock(spec=HistoryEventQueue)

    with (
        patch(
            'rotkehlchen.exchanges.exchange.DBQueryRanges.get_location_query_ranges',
            return_value=[(Timestamp(1), Timestamp(2))],
        ),
        patch('rotkehlchen.exchanges.exchange.HistoryEventQueue', return_value=event_queue),
        patch('rotkehlchen.exchanges.exchange.ts_now', return_value=Timestamp(2)),
        pytest.raises(type(error), match='query failed'),
    ):
        ExchangeWithoutApiSecret.query_history_events(exchange)

    event_queue.flush.assert_called_once_with(queried_until_ts=None)
    assert exchange.send_history_events_status_msg.call_args_list[-1].kwargs == {
        'step': HistoryEventsStep.QUERYING_EVENTS_FINISHED,
    }


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_balances_from_amounts_batches_and_uses_cache(inquirer: Any) -> Any:
    """Test that the exchange pricing helper queries all asset prices in a single
    batched oracle query and that subsequent calls (e.g. from the next exchange in
    a balance refresh) get the already priced assets from the price cache, querying
    the oracle only for the new ones"""
    oracle_queries = []

    def mock_oracle_batch(from_assets: Any, to_asset: Any) -> Any:
        oracle_queries.append(set(from_assets))
        return {from_asset: Price(FVal(100)) for from_asset in from_assets}

    eth, btc, usdc = (x.resolve_to_asset_with_oracles() for x in (A_ETH, A_BTC, A_USDC))
    with patch.object(
        inquirer._coingecko,
        'query_multiple_current_prices',
        side_effect=mock_oracle_batch,
    ):
        balances = ExchangeWithoutApiSecret.balances_from_amounts({eth: FVal(2), btc: ONE})
        assert oracle_queries == [{eth, btc}]  # one batched query for all assets
        assert balances == {
            eth: Balance(amount=FVal(2), value=FVal(200)),
            btc: Balance(amount=ONE, value=FVal(100)),
        }

        balances = ExchangeWithoutApiSecret.balances_from_amounts({btc: FVal(3), usdc: FVal(4)})
        assert oracle_queries == [{eth, btc}, {usdc}]  # btc was served from the cache
        assert balances == {
            btc: Balance(amount=FVal(3), value=FVal(300)),
            usdc: Balance(amount=FVal(4), value=FVal(400)),
        }
