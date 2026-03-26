from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.manager import HistoryQueryingManager
from rotkehlchen.types import Timestamp


@contextmanager
def _dummy_ctx():
    yield object()


def test_hyperliquid_history_failed_query_does_not_advance_ranges() -> None:
    manager = HistoryQueryingManager.__new__(HistoryQueryingManager)

    address = '0x000000000000000000000000000000000000dEaD'
    db = MagicMock()
    db.conn.read_ctx.side_effect = _dummy_ctx
    db.user_write.side_effect = _dummy_ctx
    db.get_single_blockchain_addresses.return_value = [address]
    manager.db = db
    manager.msg_aggregator = MagicMock()

    ranges = MagicMock()
    ranges.get_location_query_ranges.return_value = [(Timestamp(0), Timestamp(10))]
    history_db = MagicMock()
    hyperliquid = MagicMock()
    hyperliquid.query_history_events.side_effect = RemoteError('boom')

    with (
        patch('rotkehlchen.history.manager.DBQueryRanges', return_value=ranges),
        patch('rotkehlchen.history.manager.DBHistoryEvents', return_value=history_db),
        patch('rotkehlchen.history.manager.HyperliquidAPI', return_value=hyperliquid),
    ):
        manager._query_hyperliquid_history(start_ts=Timestamp(0), end_ts=Timestamp(10))

    history_db.add_history_events.assert_not_called()
    ranges.update_used_query_range.assert_not_called()
    manager.msg_aggregator.add_error.assert_called_once()


def test_hyperliquid_history_success_stores_events_and_updates_range() -> None:
    """On success, events are stored and query range is advanced."""
    manager = HistoryQueryingManager.__new__(HistoryQueryingManager)

    address = '0x000000000000000000000000000000000000dEaD'
    db = MagicMock()
    db.conn.read_ctx.side_effect = _dummy_ctx
    db.user_write.side_effect = _dummy_ctx
    db.get_single_blockchain_addresses.return_value = [address]
    manager.db = db
    manager.msg_aggregator = MagicMock()

    ranges = MagicMock()
    ranges.get_location_query_ranges.return_value = [(Timestamp(0), Timestamp(100))]
    history_db = MagicMock()
    fake_events = [MagicMock()]
    hyperliquid = MagicMock()
    hyperliquid.query_history_events.return_value = fake_events

    with (
        patch('rotkehlchen.history.manager.DBQueryRanges', return_value=ranges),
        patch('rotkehlchen.history.manager.DBHistoryEvents', return_value=history_db),
        patch('rotkehlchen.history.manager.HyperliquidAPI', return_value=hyperliquid),
    ):
        manager._query_hyperliquid_history(start_ts=Timestamp(0), end_ts=Timestamp(100))

    # events should have been stored
    history_db.add_history_events.assert_called_once()
    stored_events = history_db.add_history_events.call_args[1]['history']
    assert stored_events == fake_events
    # range should have been updated
    ranges.update_used_query_range.assert_called_once()
    update_args = ranges.update_used_query_range.call_args[1]
    assert update_args['location_string'] == f'hyperliquid_{address}'
    assert update_args['queried_ranges'] == [(Timestamp(0), Timestamp(100))]


def test_hyperliquid_history_no_addresses_skips() -> None:
    """If no Hyperliquid addresses are tracked, nothing happens."""
    manager = HistoryQueryingManager.__new__(HistoryQueryingManager)

    db = MagicMock()
    db.conn.read_ctx.side_effect = _dummy_ctx
    db.get_single_blockchain_addresses.return_value = []
    manager.db = db
    manager.msg_aggregator = MagicMock()

    hyperliquid = MagicMock()

    with patch('rotkehlchen.history.manager.HyperliquidAPI', return_value=hyperliquid):
        manager._query_hyperliquid_history(start_ts=Timestamp(0), end_ts=Timestamp(100))

    hyperliquid.query_history_events.assert_not_called()
