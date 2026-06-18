"""Concurrency seam for the gevent removal migration.

Business-logic code that needs to run work concurrently must go through this
module instead of importing gevent directly (enforced via ruff TID251). The
implementation is currently backed by gevent greenlets; at the migration flip
it switches to worker-thread futures without any call site changing. Call
sites must therefore only interact with task handles through the functions
defined here and never use greenlet attributes directly.

See docs/designs/gevent_to_asyncio.md for the overall plan.
"""
from collections.abc import Callable, Sequence
from typing import Any, TypeAlias

import gevent

Task: TypeAlias = gevent.Greenlet


def spawn(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Task:
    """Run func concurrently and return an opaque handle to the running task"""
    return gevent.spawn(func, *args, **kwargs)


def spawn_later(seconds: float, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Task:
    """Like spawn, but the task starts only after the given delay in seconds"""
    return gevent.spawn_later(seconds, func, *args, **kwargs)


def wait(tasks: Sequence[Task], timeout: float | None = None) -> None:
    """Block until all given tasks have finished, swallowing their exceptions.

    Inspect failures afterwards via exception_of() or result_of().
    """
    gevent.joinall(tasks, timeout=timeout, raise_error=False)


def exception_of(task: Task) -> BaseException | None:
    """Return the exception a finished task died with, or None if it succeeded"""
    return task.exception


def result_of(task: Task) -> Any:
    """Return the result of a finished task, raising the exception it died with"""
    return task.get()
