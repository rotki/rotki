import logging
import threading
import traceback
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.api.websockets.typedefs import BackgroundTaskKind, WSMessageType
from rotkehlchen.concurrency import (
    DEFAULT_CANCEL_GRACE_SECONDS,
    CancellationToken,
    Task,
    TaskCancelledError,
    wait,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

TASK_ID_MODULUS: Final = 2 ** 32


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
        # Not reset at logout, so an id stays unique across logins: started_at has one-second
        # resolution and names repeat, so neither can tell two tasks apart for a client
        self._last_task_id = 0
        # Non-None from the moment clear() starts cancelling at logout/shutdown
        # until the next session unlocks: a task registered in that window (e.g.
        # spawned by a still-live abandoned thread) is cancelled on the spot, so
        # it cannot escape into the next session with a fresh uncancelled token.
        # Mirrors RestAPI.api_tasks_stop_reason for the api-task path.
        self.stop_reason: str | None = None

    def add(
            self,
            task_name: str,
            task: Task,
            exception_is_error: bool,
            kind: BackgroundTaskKind = BackgroundTaskKind.OTHER,
            subject: dict[str, str | int] | None = None,
    ) -> None:
        task.task_name = task_name
        task.exception_is_error = exception_is_error
        task.kind = kind
        task.subject = subject if subject is not None else {}
        task.add_done_callback(self._handle_finished_task)
        with self.lock:
            self._last_task_id = self._last_task_id % TASK_ID_MODULUS + 1  # 0 means not registered
            task.supervisor_id = self._last_task_id
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
            *,
            kind: BackgroundTaskKind = BackgroundTaskKind.OTHER,
            subject: dict[str, str | int] | None = None,
            **kwargs: Any,
    ) -> Task:
        """Spawn a tracked task. `kind` and `subject` say what it works on for clients, and
        are not passed to `method`. `subject` must hold plain values: it is sent as JSON, and
        a message that does not serialize cannot be held for a client that is not connected.
        """
        log.debug('Spawning task manager task "%s"', task_name)
        task = Task(
            name=task_name,
            target=method,
            kwargs=kwargs,
            delay=after_seconds,
            token=CancellationToken(),
        )
        self.add(task_name, task, exception_is_error, kind=kind, subject=subject)
        self._notify_task_status(task, 'started')  # before start so it cannot follow 'finished'
        return task.start()

    def has_task(self, name: str) -> bool:
        """Check if there is a running task with the given name"""
        return len(self.running_tasks(name)) != 0

    def running_tasks(self, name: str) -> list[Task]:
        """The running tasks whose name starts with the given name"""
        with self.lock:
            return [task for task in self.tasks if task.dead is False and task.task_name.startswith(name)]  # noqa: E501

    def running_tasks_info(self) -> list[dict[str, Any]]:
        """The running task manager tasks a client shows, which leaves out upkeep"""
        with self.lock:
            return [
                self._task_info(task) for task in self.tasks
                if task.dead is False and task.kind != BackgroundTaskKind.OTHER
            ]

    @staticmethod
    def _task_info(task: Task) -> dict[str, Any]:
        return {
            'id': task.supervisor_id,
            'kind': task.kind,
            'name': task.task_name,
            'started_at': task.started_at,
            'subject': task.subject,
        }

    def _notify_task_status(self, task: Task, status: str) -> None:
        """Tell connected clients about a task manager task starting or ending. Not sent
        while logging out, and upkeep (kind OTHER) only reports a failure with an error.

        Only a failure with an error is held for a client that is not connected, which
        must still learn of it. The rest is dropped: a client that connects afterwards
        gets the running tasks from the periodic data instead."""
        if self.stop_reason is not None:
            return

        has_error = status == 'failed' and task.exception_is_error and task.exception is not None
        if task.kind == BackgroundTaskKind.OTHER and not has_error:
            return

        data = self._task_info(task) | {'status': status}
        if has_error:
            data['error'] = str(task.exception) or type(task.exception).__name__

        self.msg_aggregator.add_message(
            message_type=WSMessageType.BACKGROUND_TASK_STATUS,
            data=data,
        )

    def _handle_finished_task(self, task: Task) -> None:
        self._notify_task_status(task, self._finished_status(task))
        self._log_finished_task(task)

    @staticmethod
    def _finished_status(task: Task) -> str:
        if task.exception is None:
            return 'finished'
        if isinstance(task.exception, TaskCancelledError) or (
            task.cancellation_token is not None and task.cancellation_token.cancelled
        ):
            return 'cancelled'
        return 'failed'

    def _log_finished_task(self, task: Task) -> None:
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
