
import pytest

from rotkehlchen.db.updates import RotkiDataUpdater
from rotkehlchen.tasks.manager import TaskManager


class MockPremiumSyncManager:

    def __init__(self):
        pass

    def maybe_upload_data_to_server(self) -> None:
        pass


@pytest.fixture(name='max_tasks_num')
def fixture_max_tasks_num() -> int:
    """The max number of tasks below which the manager can schedule tasks

    By default -1 which disables the task manager
    """
    return -1


@pytest.fixture(name='api_task_greenlets')
def fixture_api_task_greenlets() -> list:
    return []


@pytest.fixture(name='task_manager')
def fixture_task_manager(
        database,
        blockchain,
        max_tasks_num,
        greenlet_manager,
        api_task_greenlets,
        cryptocompare,
        exchange_manager,
        messages_aggregator,
        use_function_scope_msg_aggregator,
        function_scope_messages_aggregator,
        username,
) -> TaskManager:
    msg_aggregator = function_scope_messages_aggregator if use_function_scope_msg_aggregator else messages_aggregator  # noqa: E501
    task_manager = TaskManager(
        max_tasks_num=max_tasks_num,
        greenlet_manager=greenlet_manager,
        api_task_greenlets=api_task_greenlets,
        database=database,
        cryptocompare=cryptocompare,
        premium_sync_manager=MockPremiumSyncManager(),  # type: ignore
        chains_aggregator=blockchain,
        exchange_manager=exchange_manager,
        deactivate_premium=lambda: None,
        query_balances=lambda: None,
        activate_premium=lambda _: None,
        msg_aggregator=msg_aggregator,
        data_updater=RotkiDataUpdater(msg_aggregator=msg_aggregator, user_db=database),
        username=username,
    )
    task_manager.should_schedule = True
    return task_manager
