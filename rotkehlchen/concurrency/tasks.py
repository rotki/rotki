"""Concurrency seam for the gevent removal migration.

Business-logic code that needs to run work concurrently must go through this
module (gevent imports stay banned via ruff TID251 so it cannot creep back).
Since phase 5 of the migration tasks are backed by threads -- real ones since
the phase-6 flip removed the monkeypatching. Call sites must only interact
with task handles through the Task API defined here.

Threads cannot be killed: a task that must stop early is cancelled through its
CancellationToken (see rotkehlchen.concurrency.cancellation) and exits at its
next checkpoint. Consequently every wait here is a join with an optional
timeout, never a kill.

See docs/designs/gevent_to_asyncio.md for the overall plan.
"""
import sys
import threading
import time
from collections.abc import Callable, Sequence
from types import TracebackType
from typing import Any

from rotkehlchen.concurrency.cancellation import (
    CancellationToken,
    cancellable_sleep,
    current_token,
    run_cancellable,
)

ExcInfo = tuple[type[BaseException], BaseException, TracebackType]


class Task:
    """Handle to a unit of work running on its own daemon thread.

    Replaces the gevent.Greenlet handle. The target's kwargs are kept on the
    handle (as greenlet.kwargs was) so orchestration code can identify what a
    task is working on, e.g. to cancel transaction queries for an address
    that is being removed.

    The thread does not start on construction: callers attach bookkeeping
    attributes and done-callbacks first and then call start(), so a callback
    can never observe a half-initialized handle once threads really preempt.
    """

    def __init__(
            self,
            name: str,
            target: Callable[..., Any],
            args: tuple[Any, ...] = (),
            kwargs: dict[str, Any] | None = None,
            delay: float | None = None,
            token: CancellationToken | None = None,
    ) -> None:
        self.task_name = name
        self.kwargs = kwargs if kwargs is not None else {}
        self.cancellation_token = token
        self.exception: BaseException | None = None
        self.exc_info: ExcInfo | None = None
        # bookkeeping set by the orchestration layers after construction
        self.task_id: int | None = None  # the REST async-query task id
        self.api_command: Callable[..., Any] | None = None  # the REST command, inspected by cancellation paths  # noqa: E501
        self.exception_is_error: bool = True  # whether the task supervisor logs a death as error
        self._target = target
        self._args = args
        self._delay = delay
        self._result: Any = None
        self._dead = False
        self._callbacks: list[Callable[[Task], None]] = []
        self._callback_lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, name=name, daemon=True)

    def start(self) -> 'Task':
        self._thread.start()
        return self

    @property
    def dead(self) -> bool:
        """True once the task has finished, whether it succeeded, died with an
        exception or got cancelled. False while pending in its start delay."""
        return self._dead

    def add_done_callback(self, callback: Callable[['Task'], None]) -> None:
        """Register a callback invoked with this task once it finishes.

        Runs on the task's own thread. If the task has already finished the
        callback is invoked immediately on the calling thread.
        """
        with self._callback_lock:
            if self._dead is False:
                self._callbacks.append(callback)
                return
        callback(self)

    def join(self, timeout: float | None = None) -> None:
        """Wait for the task to finish, or for the timeout to expire"""
        self._thread.join(timeout)

    def request_cancellation(self, reason: str) -> bool:
        """Request cooperative cancellation of this task.

        Returns True if the task carries a cancellation token (set by whoever
        spawned it) and cancellation was requested, False otherwise. The task
        dies with TaskCancelledError at its next checkpoint -- callers that
        need it gone must join it afterwards.
        """
        if self.cancellation_token is None:
            return False

        self.cancellation_token.cancel(reason)
        return True

    def get(self) -> Any:
        """Block until the task finishes and return its result, raising the
        exception it died with"""
        self._thread.join()
        if self.exception is not None:
            raise self.exception
        return self._result

    def _body(self) -> None:
        if self._delay is not None:
            # with a token this aborts the wait on cancellation; without one
            # it is a plain sleep, matching the old spawn_later semantics
            cancellable_sleep(self._delay)
        self._result = self._target(*self._args, **self.kwargs)

    def _run(self) -> None:
        try:
            if self.cancellation_token is not None:
                run_cancellable(self.cancellation_token, self._body)
            else:
                self._body()
        except BaseException as e:  # capture any death, incl. TaskCancelledError (BaseException)
            self.exception = e
            self.exc_info = sys.exc_info()  # type: ignore[assignment]  # an exception is active here

        with self._callback_lock:
            self._dead = True
            callbacks = self._callbacks

        for callback in callbacks:
            callback(self)


def spawn(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Task:
    """Run func concurrently and return a handle to the running task.

    If the spawning task is cancellable, the child shares its cancellation
    token: cancelling the parent cancels the whole task tree. The token has to
    be propagated explicitly since neither threads nor greenlets inherit
    contextvars.
    """
    return Task(
        name=getattr(func, '__qualname__', str(func)),
        target=func,
        args=args,
        kwargs=kwargs,
        token=current_token(),
    ).start()


def spawn_later(seconds: float, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Task:
    """Like spawn, but the task starts only after the given delay in seconds"""
    return Task(
        name=getattr(func, '__qualname__', str(func)),
        target=func,
        args=args,
        kwargs=kwargs,
        delay=seconds,
        token=current_token(),
    ).start()


def wait(tasks: Sequence[Task], timeout: float | None = None) -> None:
    """Block until all given tasks have finished or the shared timeout has
    expired, swallowing their exceptions.

    Inspect failures afterwards via exception_of() or result_of().
    """
    if timeout is None:
        for task in tasks:
            task.join()
        return

    deadline = time.monotonic() + timeout
    for task in tasks:
        if (remaining := deadline - time.monotonic()) <= 0:
            return
        task.join(remaining)


def exception_of(task: Task) -> BaseException | None:
    """Return the exception a finished task died with, or None if it succeeded"""
    return task.exception


def result_of(task: Task) -> Any:
    """Return the result of a finished task, raising the exception it died with"""
    return task.get()


def run_in_native_thread(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Run func and return its result. A direct call since the gevent flip:
    the caller already runs on a real OS thread, so CPU-bound work (e.g. DB
    compression/encryption) no longer freezes a cooperative scheduler. Kept as
    a seam so call sites document the offload intent; removed in phase 7."""
    return func(*args, **kwargs)
