from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from rotkehlchen.chain.evm.manager import EvmManager
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.hyperliquid.manager import HyperliquidManager
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.types import Timestamp


@contextmanager
def _dummy_ctx():
    yield object()


def test_query_proprietary_history_for_tracked_accounts_delegates() -> None:
    manager = HyperliquidManager.__new__(HyperliquidManager)

    address = string_to_evm_address('0x000000000000000000000000000000000000dEaD')
    db = MagicMock()
    db.conn.read_ctx.side_effect = _dummy_ctx
    db.get_single_blockchain_addresses.return_value = [address]
    manager.node_inquirer = MagicMock(database=db)

    with patch.object(
        HyperliquidManager,
        'query_proprietary_history',
    ) as query_proprietary_history:
        manager.query_proprietary_history_for_tracked_accounts(
            from_timestamp=Timestamp(0),
            to_timestamp=Timestamp(100),
        )

    query_proprietary_history.assert_called_once_with(
        addresses=[address],
        from_timestamp=Timestamp(0),
        to_timestamp=Timestamp(100),
    )


def test_query_proprietary_history_for_tracked_accounts_no_addresses_skips() -> None:
    manager = HyperliquidManager.__new__(HyperliquidManager)

    db = MagicMock()
    db.conn.read_ctx.side_effect = _dummy_ctx
    db.get_single_blockchain_addresses.return_value = []
    manager.node_inquirer = MagicMock(database=db)

    with patch.object(
        HyperliquidManager,
        'query_proprietary_history',
    ) as query_proprietary_history:
        manager.query_proprietary_history_for_tracked_accounts(
            from_timestamp=Timestamp(0),
            to_timestamp=Timestamp(100),
        )

    query_proprietary_history.assert_not_called()


def test_query_proprietary_history_failed_query_does_not_advance_ranges() -> None:
    manager = HyperliquidManager.__new__(HyperliquidManager)

    address = string_to_evm_address('0x000000000000000000000000000000000000dEaD')
    db = MagicMock()
    db.conn.read_ctx.side_effect = _dummy_ctx
    db.user_write.side_effect = _dummy_ctx
    manager.node_inquirer = MagicMock(database=db)
    manager.transactions = MagicMock()

    ranges = MagicMock()
    ranges.get_location_query_ranges.return_value = [(Timestamp(0), Timestamp(10))]
    history_db = MagicMock()
    hyperliquid = MagicMock()
    hyperliquid.query_history_events.side_effect = RemoteError('boom')

    with (
        patch('rotkehlchen.chain.hyperliquid.manager.DBQueryRanges', return_value=ranges),
        patch('rotkehlchen.chain.hyperliquid.manager.DBHistoryEvents', return_value=history_db),
        patch('rotkehlchen.chain.hyperliquid.manager.HyperliquidAPI', return_value=hyperliquid),
    ):
        manager.query_proprietary_history(addresses=[address], from_timestamp=Timestamp(0), to_timestamp=Timestamp(10))  # noqa: E501

    history_db.add_history_events.assert_not_called()
    ranges.update_used_query_range.assert_not_called()
    manager.transactions.msg_aggregator.add_error.assert_called_once()


def test_query_proprietary_history_success_stores_events_and_updates_range() -> None:
    manager = HyperliquidManager.__new__(HyperliquidManager)

    address = string_to_evm_address('0x000000000000000000000000000000000000dEaD')
    db = MagicMock()
    db.conn.read_ctx.side_effect = _dummy_ctx
    db.user_write.side_effect = _dummy_ctx
    manager.node_inquirer = MagicMock(database=db)
    manager.transactions = MagicMock()

    ranges = MagicMock()
    ranges.get_location_query_ranges.return_value = [(Timestamp(0), Timestamp(100))]
    history_db = MagicMock()
    fake_events = [MagicMock()]
    hyperliquid = MagicMock()
    hyperliquid.query_history_events.return_value = fake_events

    with (
        patch('rotkehlchen.chain.hyperliquid.manager.DBQueryRanges', return_value=ranges),
        patch('rotkehlchen.chain.hyperliquid.manager.DBHistoryEvents', return_value=history_db),
        patch('rotkehlchen.chain.hyperliquid.manager.HyperliquidAPI', return_value=hyperliquid),
    ):
        manager.query_proprietary_history(addresses=[address], from_timestamp=Timestamp(0), to_timestamp=Timestamp(100))  # noqa: E501

    history_db.add_history_events.assert_called_once()
    stored_events = history_db.add_history_events.call_args[1]['history']
    assert stored_events == fake_events
    ranges.update_used_query_range.assert_called_once()
    update_args = ranges.update_used_query_range.call_args[1]
    assert update_args['location_string'] == f'hyperliquid_{address}'
    assert update_args['queried_ranges'] == [(Timestamp(0), Timestamp(100))]


def test_query_transactions_also_queries_proprietary_history() -> None:
    manager = HyperliquidManager.__new__(HyperliquidManager)
    addresses = [string_to_evm_address('0x000000000000000000000000000000000000dEaD')]

    with (
        patch.object(EvmManager, 'query_transactions') as query_evm_transactions,
        patch.object(HyperliquidManager, 'query_proprietary_history') as query_proprietary_history,
    ):
        manager.query_transactions(
            addresses=addresses,
            from_timestamp=Timestamp(1),
            to_timestamp=Timestamp(2),
        )

    query_evm_transactions.assert_called_once_with(
        addresses=addresses,
        from_timestamp=Timestamp(1),
        to_timestamp=Timestamp(2),
    )
    query_proprietary_history.assert_called_once_with(
        addresses=addresses,
        from_timestamp=Timestamp(1),
        to_timestamp=Timestamp(2),
    )
