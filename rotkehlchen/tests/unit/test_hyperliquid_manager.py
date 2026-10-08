from contextlib import contextmanager
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.api.services.transactions import TransactionsService
from rotkehlchen.chain.evm.manager import EvmManager
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.hyperliquid.manager import (
    HYPERLIQUID_CORE_HISTORY_RANGE_PREFIX,
    HyperliquidManager,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.errors.misc import IncompleteTransactionsQuery, RemoteError
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import Location, SupportedBlockchain, Timestamp, TimestampMS

if TYPE_CHECKING:
    from collections.abc import Iterator

    from rotkehlchen.db.dbhandler import DBHandler

ADDRESS = string_to_evm_address('0x000000000000000000000000000000000000dEaD')


@contextmanager
def _dummy_ctx():
    yield object()


def _event(group_identifier: str) -> HistoryEvent:
    return HistoryEvent(
        group_identifier=group_identifier,
        sequence_index=0,
        timestamp=TimestampMS(5000),
        location=Location.HYPERLIQUID,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ONE,
        location_label=ADDRESS,
    )


def _batch_query(
        *batches: list[HistoryBaseEntry],
        error: RemoteError | None = None,
) -> MagicMock:
    """Mock a batch query that yields the given batches and then raises the error, if any."""
    def query(**kwargs: Any) -> Iterator[list[HistoryBaseEntry]]:
        yield from batches
        if error is not None:
            raise error

    return MagicMock(side_effect=query)


def _manager_with_db(database: DBHandler) -> tuple[HyperliquidManager, MagicMock]:
    """Return a manager on the given database and its mocked `add_error`."""
    manager = HyperliquidManager.__new__(HyperliquidManager)
    manager.node_inquirer = MagicMock(database=database)
    manager.transactions = MagicMock(msg_aggregator=MagicMock(add_error=(add_error := MagicMock())))  # noqa: E501
    return manager, add_error


def _stored_group_identifiers(database: DBHandler) -> list[str]:
    with database.conn.read_ctx() as cursor:
        return [row[0] for row in cursor.execute(
            'SELECT group_identifier FROM history_events ORDER BY group_identifier',
        )]


def _queried_range(database: DBHandler) -> tuple[Timestamp, Timestamp] | None:
    with database.conn.read_ctx() as cursor:
        return database.get_used_query_range(
            cursor=cursor,
            name=f'{HYPERLIQUID_CORE_HISTORY_RANGE_PREFIX}_{ADDRESS}',
        )


def test_query_proprietary_history_failure_midway_keeps_saved_pages_but_not_the_range(
        database: DBHandler,
) -> None:
    """A failure after some pages keeps the pages saved so far, but leaves the range
    unqueried so that the next sync queries all of it again."""
    manager, add_error = _manager_with_db(database)
    (hyperliquid := MagicMock()).iter_history_event_batches = _batch_query(
        [_event('page1')],
        error=RemoteError('boom'),
    )
    with patch('rotkehlchen.chain.hyperliquid.manager.HyperliquidAPI', return_value=hyperliquid):
        manager.query_proprietary_history(addresses=[ADDRESS], from_timestamp=Timestamp(0), to_timestamp=Timestamp(10))  # noqa: E501

    assert _stored_group_identifiers(database) == ['page1']
    assert _queried_range(database) is None
    assert add_error.call_args.args[0] == (
        f'Failed to query Hyperliquid history for {ADDRESS}. Will retry in a future sync.'
    )

    hyperliquid.iter_history_event_batches = _batch_query([_event('page1')], [_event('page2')])
    with patch('rotkehlchen.chain.hyperliquid.manager.HyperliquidAPI', return_value=hyperliquid):
        manager.query_proprietary_history(addresses=[ADDRESS], from_timestamp=Timestamp(0), to_timestamp=Timestamp(10))  # noqa: E501

    hyperliquid.iter_history_event_batches.assert_called_once_with(
        address=ADDRESS,
        start_ts=Timestamp(0),
        end_ts=Timestamp(10),
    )
    assert _stored_group_identifiers(database) == ['page1', 'page2']
    assert _queried_range(database) == (0, 10)
    add_error.assert_called_once()


def test_query_proprietary_history_only_queries_the_missing_ranges(database: DBHandler) -> None:
    manager, _ = _manager_with_db(database)
    (hyperliquid := MagicMock()).iter_history_event_batches = _batch_query()
    with database.user_write() as write_cursor:
        database.update_used_query_range(
            write_cursor=write_cursor,
            name=f'{HYPERLIQUID_CORE_HISTORY_RANGE_PREFIX}_{ADDRESS}',
            start_ts=Timestamp(0),
            end_ts=Timestamp(10),
        )

    with patch('rotkehlchen.chain.hyperliquid.manager.HyperliquidAPI', return_value=hyperliquid):
        manager.query_proprietary_history(addresses=[ADDRESS], from_timestamp=Timestamp(5), to_timestamp=Timestamp(20))  # noqa: E501

    hyperliquid.iter_history_event_batches.assert_called_once_with(
        address=ADDRESS,
        start_ts=Timestamp(11),
        end_ts=Timestamp(20),
    )
    assert _queried_range(database) == (0, 20)


def test_refetch_proprietary_history_ignores_query_ranges(database: DBHandler) -> None:
    manager, _ = _manager_with_db(database)
    (hyperliquid := MagicMock()).iter_history_event_batches = _batch_query(
        [_event('page1'), _event('page1b')],
        [_event('page2')],
    )
    with patch('rotkehlchen.chain.hyperliquid.manager.HyperliquidAPI', return_value=hyperliquid):
        assert manager.refetch_proprietary_history(
            address=ADDRESS,
            start_ts=Timestamp(0),
            end_ts=Timestamp(100),
        ) == 3

    hyperliquid.iter_history_event_batches.assert_called_once_with(
        address=ADDRESS,
        start_ts=Timestamp(0),
        end_ts=Timestamp(100),
    )
    assert _queried_range(database) is None


def test_refetch_proprietary_history_failure_keeps_the_refetched_pages(
        database: DBHandler,
) -> None:
    manager, _ = _manager_with_db(database)
    (hyperliquid := MagicMock()).iter_history_event_batches = _batch_query(
        [_event('page1')],
        error=RemoteError('boom'),
    )
    with (
        patch('rotkehlchen.chain.hyperliquid.manager.HyperliquidAPI', return_value=hyperliquid),
        pytest.raises(RemoteError),
    ):
        manager.refetch_proprietary_history(
            address=ADDRESS,
            start_ts=Timestamp(0),
            end_ts=Timestamp(100),
        )

    assert _stored_group_identifiers(database) == ['page1']


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


def test_incomplete_evm_query_wins_over_failed_proprietary_history() -> None:
    """An incomplete EVM query must reach the task even if the core history fails too.

    The core history is still queried, and its RemoteError is reported to the user by
    query_proprietary_history rather than replacing the incomplete query error, which the
    frontend uses to mark the addresses failed.
    """
    manager = HyperliquidManager.__new__(HyperliquidManager)
    db = MagicMock()
    db.conn.read_ctx.side_effect = _dummy_ctx
    manager.node_inquirer = MagicMock(database=db)
    manager.transactions = MagicMock()
    (ranges := MagicMock()).get_location_query_ranges.return_value = [(Timestamp(1), Timestamp(2))]
    (hyperliquid := MagicMock()).iter_history_event_batches = _batch_query(error=RemoteError('core history down'))  # noqa: E501
    with (
        patch.object(EvmManager, 'query_transactions', side_effect=IncompleteTransactionsQuery('incomplete')),  # noqa: E501
        patch('rotkehlchen.chain.hyperliquid.manager.DBQueryRanges', return_value=ranges),
        patch('rotkehlchen.chain.hyperliquid.manager.DBHistoryEvents'),
        patch('rotkehlchen.chain.hyperliquid.manager.HyperliquidAPI', return_value=hyperliquid),
        pytest.raises(IncompleteTransactionsQuery),
    ):
        manager.query_transactions(
            addresses=[string_to_evm_address('0x000000000000000000000000000000000000dEaD')],
            from_timestamp=Timestamp(1),
            to_timestamp=Timestamp(2),
        )

    hyperliquid.iter_history_event_batches.assert_called_once()
    manager.transactions.msg_aggregator.add_error.assert_called_once()


def test_query_proprietary_history_saves_events_of_an_asset_missing_from_the_user_db(
        database: DBHandler,
) -> None:
    """An event whose asset is in the global DB but not in the user DB must still be saved
    and the range committed, instead of being skipped with its range marked as queried."""
    manager, add_error = _manager_with_db(database)
    (hyperliquid := MagicMock()).iter_history_event_batches = _batch_query([_event('a')])
    with database.user_write() as write_cursor:
        write_cursor.execute('DELETE FROM assets WHERE identifier=?', (A_ETH.identifier,))

    with patch('rotkehlchen.chain.hyperliquid.manager.HyperliquidAPI', return_value=hyperliquid):
        manager.query_proprietary_history(addresses=[ADDRESS], from_timestamp=Timestamp(0), to_timestamp=Timestamp(10))  # noqa: E501

    assert _stored_group_identifiers(database) == ['a']
    assert _queried_range(database) == (0, 10)
    add_error.assert_not_called()
