from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from rotkehlchen.api.services.transactions import TransactionsService
from rotkehlchen.chain.evm.manager import EvmManager
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.hyperliquid.manager import (
    HYPERLIQUID_CORE_HISTORY_RANGE_PREFIX,
    HyperliquidManager,
)
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.types import SupportedBlockchain, Timestamp


@contextmanager
def _dummy_ctx():
    yield object()


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
    assert update_args['location_string'] == f'{HYPERLIQUID_CORE_HISTORY_RANGE_PREFIX}_{address}'
    assert update_args['queried_ranges'] == [(Timestamp(0), Timestamp(100))]


def test_query_proprietary_history_uses_core_specific_range_key() -> None:
    manager = HyperliquidManager.__new__(HyperliquidManager)
    address = string_to_evm_address('0x000000000000000000000000000000000000dEaD')
    db = MagicMock()
    db.conn.read_ctx.side_effect = _dummy_ctx
    db.user_write.side_effect = _dummy_ctx
    manager.node_inquirer = MagicMock(database=db)
    manager.transactions = MagicMock()

    ranges = MagicMock()
    ranges.get_location_query_ranges.return_value = []

    with (
        patch('rotkehlchen.chain.hyperliquid.manager.DBQueryRanges', return_value=ranges),
        patch('rotkehlchen.chain.hyperliquid.manager.DBHistoryEvents'),
        patch('rotkehlchen.chain.hyperliquid.manager.HyperliquidAPI'),
    ):
        manager.query_proprietary_history(
            addresses=[address],
            from_timestamp=Timestamp(10),
            to_timestamp=Timestamp(20),
        )

    assert ranges.get_location_query_ranges.call_args[1]['location_string'] == (
        f'{HYPERLIQUID_CORE_HISTORY_RANGE_PREFIX}_{address}'
    )


def test_refetch_proprietary_history_ignores_query_ranges() -> None:
    manager = HyperliquidManager.__new__(HyperliquidManager)

    address = string_to_evm_address('0x000000000000000000000000000000000000dEaD')
    db = MagicMock()
    db.user_write.side_effect = _dummy_ctx
    manager.node_inquirer = MagicMock(database=db)

    history_db = MagicMock()
    history_db.add_history_events.return_value = 2
    fake_events = [MagicMock(), MagicMock()]
    hyperliquid = MagicMock()
    hyperliquid.query_history_events.return_value = fake_events

    with (
        patch('rotkehlchen.chain.hyperliquid.manager.DBQueryRanges') as ranges,
        patch('rotkehlchen.chain.hyperliquid.manager.DBHistoryEvents', return_value=history_db),
        patch('rotkehlchen.chain.hyperliquid.manager.HyperliquidAPI', return_value=hyperliquid),
    ):
        assert manager.refetch_proprietary_history(
            address=address,
            start_ts=Timestamp(0),
            end_ts=Timestamp(100),
        ) == 2

    ranges.assert_not_called()
    hyperliquid.query_history_events.assert_called_once_with(
        address=address,
        start_ts=Timestamp(0),
        end_ts=Timestamp(100),
    )
    history_db.add_history_events.assert_called_once()


def test_force_refetch_transactions_also_refetches_hyperliquid_core_history() -> None:
    service = TransactionsService(rotkehlchen=MagicMock())
    address = string_to_evm_address('0x000000000000000000000000000000000000dEaD')

    with (
        patch.object(
            TransactionsService,
            '_query_txs_for_range',
            return_value=set(),
        ) as refetch_evm,
        patch.object(
            TransactionsService,
            '_refetch_hyperliquid_core_history',
            return_value=1,
        ) as refetch_core,
    ):
        result = service.force_refetch_transactions(
            chain=SupportedBlockchain.HYPERLIQUID,
            address=address,
            from_timestamp=Timestamp(0),
            to_timestamp=Timestamp(100),
        )

    refetch_evm.assert_called_once()
    refetch_core.assert_called_once_with(
        from_timestamp=Timestamp(0),
        to_timestamp=Timestamp(100),
        address=address,
    )
    assert result['result'] == {
        'new_transactions': {},
        'new_transactions_count': 0,
        'new_history_events_count': 1,
    }


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
