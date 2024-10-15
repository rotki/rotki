from collections.abc import Callable, Generator
from contextlib import contextmanager
from functools import wraps
from typing import TYPE_CHECKING, Any

from rotkehlchen.logging import enter_exit_debug_log

if TYPE_CHECKING:
    from rotkehlchen.utils.interfaces import ProgressUpdater


class ProgressContext:
    """Context class for progress manager"""

    def __init__(self) -> None:
        self.progress_handler: ProgressUpdater | None = None

    def set_progress_handler(self, handler: 'ProgressUpdater', total_steps: int) -> None:
        self.progress_handler = handler
        self.progress_handler.set_total_steps(total_steps)

    def new_step(self, description: str) -> None:
        if self.progress_handler:
            self.progress_handler.new_step(description)


progress_context = ProgressContext()


@contextmanager
def progress_manager(handler: 'ProgressUpdater', total_steps: int) -> Generator[None]:
    """Context manager for progress manager."""
    progress_context.set_progress_handler(handler, total_steps)
    yield


def progress_step(description: str) -> Callable:
    """Decorator to add new step for a function"""
    def step_decorator(function: Callable) -> Callable:
        @enter_exit_debug_log(name=function.__name__)
        @wraps(function)
        def step_wrapped(*args: Any, **kwargs: Any) -> Any:
            progress_context.new_step(description)
            return function(*args, **kwargs)
        return step_wrapped
    return step_decorator
