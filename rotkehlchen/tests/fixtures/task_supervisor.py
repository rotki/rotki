import pytest

from rotkehlchen.tasks.supervisor import TaskSupervisor


@pytest.fixture
def task_supervisor(messages_aggregator):
    manager = TaskSupervisor(msg_aggregator=messages_aggregator)
    yield manager
    manager.clear()
