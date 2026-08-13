from typing import TYPE_CHECKING, Any

import pytest

from rotkehlchen.tasks.supervisor import TaskSupervisor

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def task_supervisor(messages_aggregator: Any) -> Generator[TaskSupervisor]:
    manager = TaskSupervisor(msg_aggregator=messages_aggregator)
    yield manager
    manager.clear()
