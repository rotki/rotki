"""Asyncio utilities - replacement for gevent_compat

This module provides asyncio implementations for concurrent operations.
All calling code must use async/await patterns.
"""
import asyncio
import threading
from collections.abc import Coroutine
from contextlib import asynccontextmanager
from typing import Any

# Core async primitives
sleep = asyncio.sleep
Semaphore = asyncio.Semaphore
Event = asyncio.Event
Lock = asyncio.Lock
Queue = asyncio.Queue


# Task management
async def spawn(coro: Coroutine) -> asyncio.Task:
    """Create and return an asyncio task"""
    return asyncio.create_task(coro)


def kill(task: asyncio.Task) -> None:
    """Cancel a single task"""
    task.cancel()


def kill_all(tasks: list[asyncio.Task]) -> None:
    """Cancel all async tasks"""
    for task in tasks:
        task.cancel()


async def joinall(tasks: list[asyncio.Task], timeout: float | None = None) -> list[Any]:
    """Wait for all tasks to complete"""
    return await asyncio.gather(*tasks, return_exceptions=True)


async def wait(
    tasks: set[asyncio.Task] | None = None,
    timeout: float | None = None,
) -> tuple[set[asyncio.Task], set[asyncio.Task]]:
    """Wait for tasks to complete"""
    if tasks:
        done, pending = await asyncio.wait(tasks, timeout=timeout)
        return done, pending
    else:
        await asyncio.sleep(timeout or 0)
        return set(), set()


# Async timeout context manager
@asynccontextmanager
async def timeout(seconds: float):
    """Async timeout context manager"""
    async with asyncio.timeout(seconds):
        yield


# Task pool implementation
class Pool:
    """Simple async pool implementation"""
    def __init__(self, size: int | None = None):
        self.size = size or 10
        self._semaphore = asyncio.Semaphore(self.size)

    async def spawn(self, coro: Coroutine) -> Any:
        """Run coroutine with pool concurrency limit"""
        async with self._semaphore:
            return await coro


# Event loop utilities
def get_hub() -> asyncio.AbstractEventLoop:
    """Get the current event loop"""
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.get_event_loop()


def signal(sig: int, handler: callable) -> None:
    """Register signal handler"""
    loop = get_hub()
    loop.add_signal_handler(sig, handler)


def getcurrent() -> threading.Thread:
    """Get current context (thread in async mode)"""
    return threading.current_thread()


def get_task_name(context: threading.Thread | asyncio.Task) -> str:
    """Get a readable name for the current execution context"""
    if isinstance(context, asyncio.Task):
        return f'Task-{context.get_name()}'
    elif isinstance(context, threading.Thread):
        return f'Thread-{context.name}'
    else:
        return f'Context-{id(context)}'


def spawn_later(seconds: float, coro: Coroutine) -> asyncio.Task:
    """Schedule a coroutine to run after specified seconds"""
    async def delayed_task():
        await asyncio.sleep(seconds)
        return await coro
    return asyncio.create_task(delayed_task())


# Exception types
class ConcurrentObjectUseError(Exception):
    """Error when an object is used concurrently"""


# Type aliases for migration
Task = asyncio.Task
Greenlet = asyncio.Task  # Compatibility alias

__all__ = [
    'ConcurrentObjectUseError',
    'Event',
    'Greenlet',
    'Lock',
    'Pool',
    'Queue',
    'Semaphore',
    'Task',
    'get_hub',
    'get_task_name',
    'getcurrent',
    'joinall',
    'kill',
    'kill_all',
    'signal',
    'sleep',
    'spawn',
    'spawn_later',
    'timeout',
    'wait',
]
