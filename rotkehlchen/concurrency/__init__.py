"""Concurrency seam for the gevent removal migration.

Business-logic code that needs to run work concurrently must go through this
module instead of importing gevent directly (enforced via ruff TID251). Tasks
run on threads, which the still-active monkeypatching turns into cooperative
greenlets until the flip removes it. Call sites must only interact with task
handles through the Task API defined here.

See docs/designs/gevent_to_asyncio.md for the overall plan.
"""
from rotkehlchen.concurrency.cancellation import (
    DEFAULT_CANCEL_GRACE_SECONDS,
    CancellationToken,
    TaskCancelledError,
    cancellable_sleep,
    checkpoint,
    current_token,
    run_cancellable,
)
from rotkehlchen.concurrency.tasks import (
    Task,
    exception_of,
    result_of,
    spawn,
    spawn_later,
    wait,
)

__all__ = [
    'DEFAULT_CANCEL_GRACE_SECONDS',
    'CancellationToken',
    'Task',
    'TaskCancelledError',
    'cancellable_sleep',
    'checkpoint',
    'current_token',
    'exception_of',
    'result_of',
    'run_cancellable',
    'spawn',
    'spawn_later',
    'wait',
]
