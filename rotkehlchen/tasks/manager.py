"""Task manager using asyncio"""
import asyncio
import logging
import traceback
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from rotkehlchen.errors.misc import TaskKilledError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

T = TypeVar('T')


class TrackedTask:
    """Wrapper for asyncio.Task with additional metadata"""

    def __init__(
            self,
            task: asyncio.Task,
            name: str,
            exception_is_error: bool = True,
    ):
        self.task = task
        self.name = name
        self.exception_is_error = exception_is_error

    @property
    def done(self) -> bool:
        return self.task.done()

    @property
    def cancelled(self) -> bool:
        return self.task.cancelled()

    def cancel(self) -> bool:
        return self.task.cancel()

    def exception(self) -> BaseException | None:
        if self.task.done() and not self.task.cancelled():
            return self.task.exception()
        return None


class TaskManager:
    """Async replacement for GreenletManager using asyncio tasks"""

    def __init__(self, msg_aggregator: MessagesAggregator) -> None:
        self.msg_aggregator = msg_aggregator
        self.tasks: list[TrackedTask] = []

    def _handle_task_exception(self, task: TrackedTask) -> None:
        """Handle exceptions from completed tasks"""
        exception = task.exception()
        if exception is None:
            return

        if isinstance(exception, TaskKilledError):
            log.debug(f'Task {task.name} was cancelled')
            return

        if isinstance(exception, asyncio.CancelledError):
            log.debug(f'Task {task.name} was cancelled')
            return

        first_line = f'{task.name} died with exception: {exception}'
        if not task.exception_is_error:
            log.warning(f'{first_line} but that is not treated as an error')
            return

        msg = (
            f'{first_line}.\n'
            f'Exception Type: {type(exception).__name__}\n'
            f'Exception: {exception}\n'
            f'Traceback:\n{traceback.format_exc()}'
        )
        log.error(msg)
        self.msg_aggregator.add_error(f'{first_line}. Check the logs for more details')

    def add(
            self,
            task_name: str,
            task: asyncio.Task,
            exception_is_error: bool = True,
    ) -> TrackedTask:
        """Add a task to be tracked"""
        tracked = TrackedTask(task, task_name, exception_is_error)

        # Add callback to handle exceptions when task completes
        def done_callback(t: asyncio.Task) -> None:
            if t.exception() is not None:
                self._handle_task_exception(tracked)

        task.add_done_callback(done_callback)
        self.tasks.append(tracked)
        return tracked

    def spawn_and_track(
            self,
            after_seconds: float | None = None,
            task_name: str = '',
            exception_is_error: bool = True,
            method: Callable | None = None,
            delay: float | None = None,
            coro: Coroutine[Any, Any, T] | None = None,
            **kwargs: Any,
    ) -> TrackedTask | None:
        """Spawn and track a task - supports both old sync and new async styles

        Old gevent style:
            spawn_and_track(
                after_seconds=5,
                task_name='my task',
                method=some_function,
                arg1='value'
            )

        New async style:
            spawn_and_track(
                task_name='my task',
                coro=some_coroutine(),
                delay=5
            )
        """
        # Handle the delay parameter
        actual_delay = delay if delay is not None else after_seconds

        # New async style - called with coro parameter
        if coro is not None:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in an async context, create task directly
                    return self._create_tracked_task(
                        task_name=task_name,
                        coro=coro,
                        exception_is_error=exception_is_error,
                        delay=actual_delay,
                    )
                else:
                    # We're in a sync context, use run_coroutine_threadsafe
                    future = asyncio.run_coroutine_threadsafe(
                        self._async_spawn_and_track(
                            task_name=task_name,
                            coro=coro,
                            exception_is_error=exception_is_error,
                            delay=actual_delay,
                        ),
                        loop,
                    )
                    return future.result()
            except RuntimeError:
                # No event loop, create one
                return asyncio.run(
                    self._async_spawn_and_track(
                        task_name=task_name,
                        coro=coro,
                        exception_is_error=exception_is_error,
                        delay=actual_delay,
                    ),
                )

        # Old gevent style - called with method parameter
        if method is not None:
            # Convert sync method to async
            async def async_wrapper():
                if asyncio.iscoroutinefunction(method):
                    return await method(**kwargs)
                else:
                    # Run sync method in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, lambda: method(**kwargs))

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in an async context
                    return self._create_tracked_task(
                        task_name=task_name,
                        coro=async_wrapper(),
                        exception_is_error=exception_is_error,
                        delay=actual_delay,
                    )
                else:
                    # We're in a sync context
                    future = asyncio.run_coroutine_threadsafe(
                        self._async_spawn_and_track(
                            task_name=task_name,
                            coro=async_wrapper(),
                            exception_is_error=exception_is_error,
                            delay=actual_delay,
                        ),
                        loop,
                    )
                    return future.result()
            except RuntimeError:
                # No event loop
                return asyncio.run(
                    self._async_spawn_and_track(
                        task_name=task_name,
                        coro=async_wrapper(),
                        exception_is_error=exception_is_error,
                        delay=actual_delay,
                    ),
                )

        return None

    def _create_tracked_task(
            self,
            task_name: str,
            coro: Coroutine[Any, Any, T],
            exception_is_error: bool = True,
            delay: float | None = None,
    ) -> TrackedTask:
        """Create and track a task (must be called from async context)"""
        log.debug(f'Creating async task "{task_name}"')

        if delay is not None:
            async def delayed_coro():
                await asyncio.sleep(delay)
                return await coro
            task = asyncio.create_task(delayed_coro())
        else:
            task = asyncio.create_task(coro)

        task.set_name(task_name)
        return self.add(task_name, task, exception_is_error)

    async def _async_spawn_and_track(
            self,
            task_name: str,
            coro: Coroutine[Any, Any, T],
            exception_is_error: bool = True,
            delay: float | None = None,
    ) -> TrackedTask:
        """Internal async spawn_and_track implementation"""
        return self._create_tracked_task(task_name, coro, exception_is_error, delay)

    def clear(self) -> None:
        """Cancel all tracked tasks. To be called when logging out or shutting down"""
        for tracked_task in self.tasks:
            if not tracked_task.done:
                tracked_task.cancel()
        self.tasks.clear()

    def clear_finished(self) -> None:
        """Remove all finished tracked tasks from the list"""
        self.tasks = [t for t in self.tasks if not t.done]

    def has_task(self, name: str) -> bool:
        """Check if there is a running task with the given name"""
        for tracked_task in self.tasks:
            if not tracked_task.done and tracked_task.name.startswith(name):
                return True
        return False

    async def wait_for_all(self, timeout: float | None = None) -> None:
        """Wait for all tasks to complete

        Args:
            timeout: Maximum time to wait in seconds
        """
        if not self.tasks:
            return

        pending_tasks = [t.task for t in self.tasks if not t.done]
        if pending_tasks:
            await asyncio.wait(pending_tasks, timeout=timeout)

    def get_task_by_name(self, name: str) -> TrackedTask | None:
        """Get a running task by name"""
        for tracked_task in self.tasks:
            if not tracked_task.done and tracked_task.name == name:
                return tracked_task
        return None

    @property
    def running_tasks(self) -> list[TrackedTask]:
        """Get all currently running tasks"""
        return [t for t in self.tasks if not t.done]

    @property
    def task_count(self) -> int:
        """Get count of running tasks"""
        return len(self.running_tasks)
