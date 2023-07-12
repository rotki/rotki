import os
import signal
from types import FrameType
from typing import Callable

from .constants import INTERVAL_SECONDS

if os.name != 'nt':  # signal on windows doesn't have these attributes
    TIMER = signal.ITIMER_PROF  # type: ignore[attr-defined,unused-ignore]  # pylint: disable=no-member  # noqa: E501  # linters don't understand the os.name check
    TIMER_SIGNAL = signal.SIGPROF  # type: ignore[attr-defined,unused-ignore]  # pylint: disable=no-member  # noqa: E501  # linters don't understand the os.name check

SignalHandler = Callable[[int, FrameType], None]


class Timer:
    def __init__(
            self,
            callback: SignalHandler,
            timer: int = TIMER,
            interval: float = INTERVAL_SECONDS,
            timer_signal: int = TIMER_SIGNAL,
    ) -> None:

        assert callable(callback), 'callback must be callable'

        signal.signal(timer_signal, self.callback)  # type: ignore
        if os.name != 'nt':
            signal.setitimer(timer, interval, interval)  # type: ignore[attr-defined,unused-ignore]  # pylint: disable=no-member  # noqa: E501  # linters don't understand the os.name check

        self._callback = callback

    def callback(self, signum: int, stack: FrameType) -> None:
        self._callback(signum, stack)

    def stop(self) -> None:
        del self._callback

        signal.signal(TIMER_SIGNAL, signal.SIG_IGN)

    def __bool__(self) -> bool:
        # we're always truthy
        return True
