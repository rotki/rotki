import logging
import threading
import traceback
from collections.abc import Callable
from typing import Any

from rotkehlchen.concurrency import (
    DEFAULT_CANCEL_GRACE_SECONDS,
    CancellationToken,
    Task,
    TaskCancelledError,
    wait,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class TaskSupervisor:
    """Collects and manages the background tasks spawned by various sources.

    Replaced GreenletManager in phase 5 of the gevent removal migration
    (docs/designs/gevent_to_asyncio.md): tasks run on threads, which cannot be
    killed -- clear() cancels their tokens and gives them a grace period to
    exit at their next cancellation checkpoint.
    """

    def __init__(self, msg_aggregator: MessagesAggregator) -> None:
        self.msg_aggregator = msg_aggregator
        # guards self.tasks and stop_reason: appended to by any thread spawning
        # work while the scheduler thread prunes finished entries
        self.lock = threading.Lock()
        self.tasks: list[Task] = []
        # Non-None from the moment clear() starts cancelling at logout/shutdown
        # until the next session unlocks: a task registered in that window (e.g.
        # spawned by a still-live abandoned thread) is cancelled on the spot, so
        # it cannot escape into the next session with a fresh uncancelled token.
        # Mirrors RestAPI.api_tasks_stop_reason for the api-task path.
        self.stop_reason: str | None = None

    def add(self, task_name: str, task: Task, exception_is_error: bool) -> None:
        task.task_name = task_name
        task.exception_is_error = exception_is_error
        task.add_done_callback(self._handle_finished_task)
        with self.lock:
            self.tasks.append(task)
            if self.stop_reason is not None:
                task.request_cancellation(self.stop_reason)

    def allow_new_tasks(self) -> None:
        """Lift the cancel-at-registration latch of clear(). To be called when a
        new user session unlocks, so its tasks are no longer cancelled at birth."""
        with self.lock:
            self.stop_reason = None

    def clear(self) -> None:
        """Cancel all tracked tasks and wait a short grace period for them to
        exit at their next checkpoint. To be called when logging out or
        shutting down. A task that does not make it (e.g. stuck in a remote
        query) is abandoned: it dies at its next checkpoint and its death is
        logged without alerting the user since its token shows the
        cancellation was deliberate."""
        with self.lock:
            # from here on new tasks are cancelled at registration (see add), so
            # nothing spawned during or after the grace period below -- including
            # in the window before tasks.clear() -- escapes cancellation
            self.stop_reason = 'Cancelled due to logout or shutdown'
            pending = [task for task in self.tasks if task.dead is False]
        if len(pending) != 0:
            for task in pending:
                task.request_cancellation('Cancelled due to logout or shutdown')
            wait(pending, timeout=DEFAULT_CANCEL_GRACE_SECONDS)
            if len(survivors := [task.task_name for task in pending if task.dead is False]) != 0:
                log.warning(
                    'Abandoning cancelled tasks that did not exit within the grace period',
                    tasks=survivors,
                )
        with self.lock:
            self.tasks.clear()

    def clear_finished(self) -> None:
        """Remove all finished tracked tasks from the list"""
        with self.lock:  # in-place so a concurrent add() cannot land on a discarded list
            self.tasks[:] = [x for x in self.tasks if not x.dead]

    def spawn_and_track(
            self,
            after_seconds: float | None,
            task_name: str,
            exception_is_error: bool,
            method: Callable,
            **kwargs: Any,
    ) -> Task:
        log.debug('Spawning task manager task "%s"', task_name)
        task = Task(
            name=task_name,
            target=method,
            kwargs=kwargs,
            delay=after_seconds,
            token=CancellationToken(),
        )
        self.add(task_name, task, exception_is_error)
        return task.start()

    def has_task(self, name: str) -> bool:
        """Check if there is a running task with the given name"""
        with self.lock:
            return any(task.dead is False and task.task_name.startswith(name) for task in self.tasks)  # noqa: E501

    def _handle_finished_task(self, task: Task) -> None:
        if task.exception is None:
            log.debug('Finished task %s from task manager.', task.task_name)
            return

        if isinstance(task.exception, TaskCancelledError):
            log.debug('Task %s was cancelled', task.task_name)
            return

        if (token := task.cancellation_token) is not None and token.cancelled:
            # died at an arbitrary point after cancellation, e.g. on the closed
            # DB of a logged-out user -- expected, so no user-facing error
            log.debug(
                'Task %s died with %s after its cancellation was requested',
                task.task_name,
                task.exception,
            )
            return

        first_line = f'{task.task_name} died with exception: {task.exception}'
        if not task.exception_is_error:
            log.warning('%s but that is not treated as an error', first_line)
            return

        msg = (
            f'{first_line}.\n'
            f'Exception Name: {task.exc_info[0]}\nException Info: {task.exc_info[1]}'  # type: ignore[index]  # exc_info is set whenever exception is
            f'\nTraceback:\n {"".join(traceback.format_tb(task.exc_info[2]))}'  # type: ignore[index]
        )
        log.error(msg)
        self.msg_aggregator.add_error(f'{first_line}. Check the logs for more details')
