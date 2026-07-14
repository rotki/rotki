"""Cooperative task cancellation (phase 2 of the gevent removal migration).

Replaces `greenlet.kill()` semantics: instead of killing a task at an arbitrary
point, callers cancel its CancellationToken and the task raises
TaskCancelledError at its next checkpoint. Checkpoints are the DB progress
handler (long statements abort), cancellable_sleep() in retry/backoff loops and
explicit checkpoint() calls at pagination boundaries.

The current task's token travels in a ContextVar. Greenlets do not inherit
contextvars from their spawner (verified: each greenlet starts with an empty
context), so anything that starts a task must establish the token explicitly
via run_cancellable() -- the spawn functions in rotkehlchen.concurrency.tasks,
TaskSupervisor and the REST API async-query path all do.

See docs/designs/gevent_to_asyncio.md for the overall plan.
"""
import threading
import time
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Callable

DEFAULT_CANCEL_GRACE_SECONDS: Final = 3.0


class TaskCancelledError(BaseException):
    """Raised inside a task at a checkpoint after its token got cancelled.

    Inherits BaseException (as asyncio.CancelledError does) so that broad
    `except Exception` handlers in business logic cannot swallow a
    cancellation and keep the task running.
    """


class CancellationToken:
    """A one-shot cooperative cancellation signal shared by a task tree.

    The underlying event is a threading.Event, which is gevent-cooperative
    while the monkeypatching is in place and needs no change after the flip
    to real threads.
    """

    __slots__ = ('_event', 'reason')

    def __init__(self) -> None:
        self._event = threading.Event()
        self.reason: str | None = None

    def cancel(self, reason: str) -> None:
        """Request cancellation. Idempotent; the first reason given wins."""
        if self.reason is None:  # set reason before the event so waiters see it
            self.reason = reason
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def check(self) -> None:
        """Raise TaskCancelledError if this token has been cancelled."""
        if self._event.is_set():
            raise TaskCancelledError(self.reason)

    def sleep(self, seconds: float) -> None:
        """Sleep that is interrupted immediately when the token gets cancelled.

        May raise TaskCancelledError.
        """
        if self._event.wait(seconds):
            raise TaskCancelledError(self.reason)


_current_token: ContextVar[CancellationToken | None] = ContextVar(
    'cancellation_token',
    default=None,
)


def current_token() -> CancellationToken | None:
    """Return the cancellation token of the currently running task, if any"""
    return _current_token.get()


def checkpoint() -> None:
    """Cancellation checkpoint: raise TaskCancelledError if the current task
    has been cancelled. No-op outside a cancellable task. Cheap enough for
    per-iteration use in pagination and decoding loops."""
    if (token := _current_token.get()) is not None:
        token.check()


def cancellable_sleep(seconds: float) -> None:
    """Sleep that wakes up immediately raising TaskCancelledError if the
    current task gets cancelled. Plain sleep outside a cancellable task.
    Use this instead of time.sleep() in retry/backoff loops."""
    if (token := _current_token.get()) is not None:
        token.sleep(seconds)
    else:
        time.sleep(seconds)


def run_cancellable(
        token: CancellationToken,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
) -> Any:
    """Run func with the given token installed as the current task's token.

    Meant to be the top frame of a spawned task. Raises TaskCancelledError
    without calling func if the token was cancelled before the task started
    (e.g. a task scheduled with a delay and cancelled in the meantime).
    """
    _current_token.set(token)  # no reset: the task's context dies with it
    token.check()
    return func(*args, **kwargs)
