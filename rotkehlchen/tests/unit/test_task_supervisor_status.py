from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.concurrency import Task, current_token
from rotkehlchen.tasks.supervisor import TaskSupervisor
from rotkehlchen.types import Timestamp

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


@pytest.mark.parametrize(('method', 'final_status'), [
    (_succeed, 'finished'),
    (_fail, 'failed'),
    (_die_after_cancel, 'cancelled'),
])
def test_task_start_and_end_are_sent(method: Callable[[], None], final_status: str) -> None:
    supervisor, msg_aggregator = _supervisor()
    supervisor.spawn_and_track(
        after_seconds=None, task_name='my task', exception_is_error=False, method=method,
    ).join()
    calls = msg_aggregator.add_message.call_args_list
    assert [c.kwargs['data']['status'] for c in calls] == ['started', final_status]
    assert all(
        c.kwargs['message_type'] == WSMessageType.BACKGROUND_TASK_STATUS and
        c.kwargs['data']['name'] == 'my task' and
        isinstance(c.kwargs['data']['started_at'], int)
        for c in calls
    )


def test_no_broadcast_while_stopping() -> None:
    supervisor, msg_aggregator = _supervisor()
    supervisor.stop_reason = 'logout'
    supervisor.spawn_and_track(
        after_seconds=None, task_name='late', exception_is_error=True, method=lambda: None,
    ).join()
    msg_aggregator.add_message.assert_not_called()


def test_running_tasks_info_lists_name_and_start_time() -> None:
    supervisor, _ = _supervisor()
    task = Task(name='x', target=lambda: None)
    task.started_at = Timestamp(5)
    supervisor.tasks.append(task)
    assert supervisor.running_tasks_info() == [{'name': 'x', 'started_at': 5}]
