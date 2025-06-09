"""Async task manager to replace GreenletManager"""
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


class AsyncTaskManager:
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
    
    async def spawn_and_track(
            self,
            task_name: str,
            coro: Coroutine[Any, Any, T],
            exception_is_error: bool = True,
            delay: float | None = None,
    ) -> TrackedTask:
        """Spawn a coroutine as a task and track it
        
        Args:
            task_name: Name for the task (for logging)
            coro: Coroutine to run
            exception_is_error: Whether exceptions should be treated as errors
            delay: Optional delay in seconds before starting the task
        """
        log.debug(f'Spawning async task "{task_name}"')
        
        if delay is not None:
            async def delayed_coro():
                await asyncio.sleep(delay)
                return await coro
            task = asyncio.create_task(delayed_coro())
        else:
            task = asyncio.create_task(coro)
            
        task.set_name(task_name)
        return self.add(task_name, task, exception_is_error)
    
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


# Compatibility layer for gradual migration
class TaskManagerMigrationBridge:
    """Bridge between sync GreenletManager and async AsyncTaskManager"""
    
    def __init__(self, msg_aggregator: MessagesAggregator):
        from rotkehlchen.greenlets.manager import GreenletManager
        
        self.greenlet_manager = GreenletManager(msg_aggregator)
        self.async_manager = AsyncTaskManager(msg_aggregator)
        self.use_async = False
        self.loop: asyncio.AbstractEventLoop | None = None
        
    def spawn_and_track(
            self,
            after_seconds: float | None,
            task_name: str,
            exception_is_error: bool,
            method: Callable,
            **kwargs: Any,
    ) -> Any:
        """Spawn task using appropriate manager"""
        if self.use_async and self.loop:
            # Convert sync method to async if needed
            if not asyncio.iscoroutinefunction(method):
                async def async_wrapper():
                    return method(**kwargs)
                coro = async_wrapper()
            else:
                coro = method(**kwargs)
                
            # Schedule in event loop
            future = asyncio.run_coroutine_threadsafe(
                self.async_manager.spawn_and_track(
                    task_name=task_name,
                    coro=coro,
                    exception_is_error=exception_is_error,
                    delay=after_seconds,
                ),
                self.loop
            )
            return future.result()
        else:
            # Use greenlet manager
            return self.greenlet_manager.spawn_and_track(
                after_seconds=after_seconds,
                task_name=task_name,
                exception_is_error=exception_is_error,
                method=method,
                **kwargs
            )
    
    def clear(self) -> None:
        """Clear all tasks"""
        if self.use_async:
            # Cancel async tasks
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self._clear_async_tasks(),
                    self.loop
                ).result()
        else:
            self.greenlet_manager.clear()
            
    async def _clear_async_tasks(self) -> None:
        """Helper to clear async tasks"""
        self.async_manager.clear()
        
    def has_task(self, name: str) -> bool:
        """Check if task exists"""
        if self.use_async:
            return self.async_manager.has_task(name)
        return self.greenlet_manager.has_task(name)