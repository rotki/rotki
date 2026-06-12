"""Concurrency seam for the gevent removal migration.

Business-logic code that needs to run work concurrently must go through this
module instead of importing gevent directly (enforced via ruff TID251). The
implementation is currently backed by gevent greenlets; at the migration flip
it switches to worker-thread futures without any call site changing. Call
sites must therefore only interact with task handles through the functions
defined here and never use greenlet attributes directly.

See docs/designs/gevent_to_asyncio.md for the overall plan.
"""
from rotkehlchen.concurrency.tasks import (
    Task,
    exception_of,
    result_of,
    spawn,
    spawn_later,
    wait,
)

__all__ = [
    'Task',
    'exception_of',
    'result_of',
    'spawn',
    'spawn_later',
    'wait',
]
