import signal
from types import FrameType
from typing import Callable

from .constants import INTERVAL_SECONDS

# TIMER_SIGNAL = signal.SIGALRM
# TIMER =  signal.ITIMER_REAL
# TIMER_SIGNAL = signal.SIGVTALRM
# TIMER =  signal.ITIMER_VIRTUAL
TIMER = signal.ITIMER_PROF
TIMER_SIGNAL = signal.SIGPROF

SignalHandler = Callable[[int, FrameType], None]


class Timer:
    def __init__(
        self,
        callback: SignalHandler,
        timer: int = TIMER,
        interval: float = INTERVAL_SECONDS,
        timer_signal: int = TIMER_SIGNAL,
    ) -> None:

        assert callable(callback), "callback must be callable"

        signal.signal(timer_signal, self.callback)
        signal.setitimer(timer, interval, interval)

        self._callback = callback

    def callback(self, signum: int, stack: FrameType) -> None:
        self._callback(signum, stack)

    def stop(self) -> None:
        del self._callback

        signal.signal(TIMER_SIGNAL, signal.SIG_IGN)

    def __bool__(self) -> bool:
        # we're always truthy
        return True
