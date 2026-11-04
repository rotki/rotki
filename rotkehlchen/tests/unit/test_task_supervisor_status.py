from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from rotkehlchen.api.websockets.typedefs import BackgroundTaskKind, WSMessageType
from rotkehlchen.concurrency import Task, current_token
from rotkehlchen.tasks.supervisor import TASK_ID_MODULUS, TaskSupervisor
from rotkehlchen.types import SupportedBlockchain, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from collections.abc import Callable


def _supervisor() -> tuple[TaskSupervisor, MagicMock]:
    msg_aggregator = MagicMock()
    return TaskSupervisor(msg_aggregator=msg_aggregator), msg_aggregator


def _succeed() -> None:
    return None


def _fail() -> None:
    raise ValueError('boom')


def _die_after_cancel() -> None:
    assert (token := current_token()) is not None
    token.cancel('removed')
    raise ValueError('closed db')


@pytest.mark.parametrize(('method', 'kind', 'exception_is_error', 'statuses', 'error'), [
    (_succeed, BackgroundTaskKind.DB_UPLOAD, False, ['started', 'finished'], None),
    (_die_after_cancel, BackgroundTaskKind.DB_UPLOAD, False, ['started', 'cancelled'], None),
    (_fail, BackgroundTaskKind.DB_UPLOAD, False, ['started', 'failed'], None),
    (_fail, BackgroundTaskKind.DB_UPLOAD, True, ['started', 'failed'], 'boom'),
    (
        MagicMock(side_effect=ValueError),  # no message, so the error names the exception
        BackgroundTaskKind.DB_UPLOAD,
        True,
        ['started', 'failed'],
        'ValueError',
    ),
    (_succeed, BackgroundTaskKind.OTHER, True, [], None),
    (_die_after_cancel, BackgroundTaskKind.OTHER, True, [], None),
    (_fail, BackgroundTaskKind.OTHER, False, [], None),
    (_fail, BackgroundTaskKind.OTHER, True, ['failed'], 'boom'),
])
def test_task_status_messages(
        method: Callable[[], None],
        kind: BackgroundTaskKind,
        exception_is_error: bool,
        statuses: list[str],
        error: str | None,
) -> None:
    supervisor, msg_aggregator = _supervisor()
    subject: dict[str, str | int] = {'chain': SupportedBlockchain.ETHEREUM.serialize(), 'count': 3}
    task = supervisor.spawn_and_track(
        after_seconds=None,
        task_name='my task',
        exception_is_error=exception_is_error,
        method=method,
        kind=kind,
        subject=subject,
    )
    task.join()
    expected = [{
        'id': 1,
        'kind': kind.value,
        'name': 'my task',
        'started_at': task.started_at,
        'status': status,
        'subject': subject,
    } for status in statuses]
    if error is not None:
        expected[-1]['error'] = error

    assert [c.kwargs['data'] for c in msg_aggregator.add_message.call_args_list] == expected
    assert all(
        c.kwargs['message_type'] == WSMessageType.BACKGROUND_TASK_STATUS
        for c in msg_aggregator.add_message.call_args_list
    )


def test_no_broadcast_while_stopping() -> None:
    supervisor, msg_aggregator = _supervisor()
    supervisor.stop_reason = 'logout'
    supervisor.spawn_and_track(
        after_seconds=None,
        task_name='late',
        exception_is_error=True,
        method=lambda: None,
        kind=BackgroundTaskKind.DB_UPLOAD,
    ).join()
    msg_aggregator.add_message.assert_not_called()


def test_kind_and_subject_do_not_reach_the_method() -> None:
    supervisor, _ = _supervisor()
    received: dict[str, int] = {}
    supervisor.spawn_and_track(
        after_seconds=None,
        task_name='my task',
        exception_is_error=True,
        method=lambda **kwargs: received.update(kwargs),
        kind=BackgroundTaskKind.DB_UPLOAD,
        subject={'count': 1},
        limit=5,
    ).join()
    assert received == {'limit': 5}


def test_ids_stay_unique_across_logins_and_wrap() -> None:
    """A task of the next login must not reuse the id of one a client still has a row for."""
    supervisor, _ = _supervisor()

    def spawn() -> Task:
        return supervisor.spawn_and_track(
            after_seconds=None, task_name='same', exception_is_error=True, method=_succeed,
        )

    first, second = spawn(), spawn()
    supervisor.clear()
    supervisor.allow_new_tasks()
    assert (first.supervisor_id, second.supervisor_id, spawn().supervisor_id) == (1, 2, 3)

    supervisor._last_task_id = TASK_ID_MODULUS - 1
    assert spawn().supervisor_id == 0


def test_only_failures_with_an_error_are_held_and_repeats_collapse() -> None:
    """Goes through a real aggregator and the real payload, so it also proves the payload
    serializes: a message that does not is logged and dropped instead of being held."""
    supervisor = TaskSupervisor(msg_aggregator=(msg_aggregator := MessagesAggregator()))
    for method, exception_is_error in (
            (_succeed, True),
            (_fail, False),
            (_fail, True),
            (_fail, True),
    ):
        supervisor.spawn_and_track(
            after_seconds=None,
            task_name='my task',
            exception_is_error=exception_is_error,
            method=method,
            kind=BackgroundTaskKind.EVM_RECEIPTS,
            subject={'chain': SupportedBlockchain.ETHEREUM.serialize(), 'count': 3},
        ).join()
    held, dropped = msg_aggregator.consume_held()
    assert dropped == 0
    assert len(held) == 1  # the status alone, with no user message reporting it a second time
    assert held[0]['type'] == WSMessageType.BACKGROUND_TASK_STATUS
    assert held[0]['count'] == 2
    assert held[0]['data']['id'] == 4
    assert held[0]['data']['kind'] == 'evm_receipts'
    assert held[0]['data']['error'] == 'boom'


def test_held_failures_of_same_named_connections_stay_apart() -> None:
    """Connection names are only unique per location, so both tasks have the same name."""
    supervisor = TaskSupervisor(msg_aggregator=(msg_aggregator := MessagesAggregator()))
    for location in ('kraken', 'binance', 'kraken'):
        supervisor.spawn_and_track(
            after_seconds=None,
            task_name='Query history of main exchange',
            exception_is_error=True,
            method=_fail,
            kind=BackgroundTaskKind.EXCHANGE_HISTORY,
            subject={'location': location, 'name': 'main'},
        ).join()
    held, dropped = msg_aggregator.consume_held()
    assert dropped == 0
    assert sorted((x['data']['subject']['location'], x['count']) for x in held) == [
        ('binance', 1),
        ('kraken', 2),
    ]


def test_running_tasks_info_leaves_out_upkeep() -> None:
    supervisor, _ = _supervisor()
    (task := Task(name='x', target=lambda: None)).started_at = Timestamp(5)
    task.supervisor_id, task.kind, task.subject = 7, BackgroundTaskKind.EVM_RECEIPTS, {'count': 2}
    (upkeep := Task(name='upkeep', target=lambda: None)).started_at = Timestamp(5)
    supervisor.tasks.extend((task, upkeep))
    assert supervisor.running_tasks_info() == [{
        'id': 7,
        'kind': 'evm_receipts',
        'name': 'x',
        'started_at': 5,
        'subject': {'count': 2},
    }]
    assert supervisor.has_task('upkeep') is True  # scheduling still sees upkeep tasks
