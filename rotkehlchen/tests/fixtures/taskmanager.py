
from typing import Any

import pytest

from rotkehlchen.db.updates import RotkiDataUpdater
from rotkehlchen.history.processing import HistoryProcessingCoordinator
from rotkehlchen.tasks.manager import TaskManager


class MockPremiumSyncManager:

    def __init__(self) -> None:
        pass

    def maybe_upload_data_to_server(self) -> None:
        pass


@pytest.fixture(name='max_tasks_num')
def fixture_max_tasks_num() -> int:
    """The max number of tasks below which the manager can schedule tasks

    By default -1 which disables the task manager
    """
    return -1


@pytest.fixture(name='api_tasks')
def fixture_api_tasks() -> list:
    return []


@pytest.fixture(name='enable_priority_tasks')
def fixture_enable_priority_tasks() -> bool:
    return False


@pytest.fixture(name='task_manager')
def fixture_task_manager(
        database: Any,
        blockchain: Any,
        max_tasks_num: int,
        task_supervisor: Any,
        api_tasks: list[Any],
        cryptocompare: Any,
        exchange_manager: Any,
        messages_aggregator: Any,
        use_function_scope_msg_aggregator: bool,
        function_scope_messages_aggregator: Any,
        username: str,
        enable_priority_tasks: bool,
) -> TaskManager:
    msg_aggregator = function_scope_messages_aggregator if use_function_scope_msg_aggregator else messages_aggregator  # noqa: E501
    task_manager = TaskManager(
        max_tasks_num=max_tasks_num,
        task_supervisor=task_supervisor,
        api_tasks=api_tasks,
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
        history_processing_coordinator=HistoryProcessingCoordinator(),
    )
    task_manager.should_schedule = True
    if enable_priority_tasks is False:
        task_manager.priority_tasks_queue.clear()
    return task_manager
