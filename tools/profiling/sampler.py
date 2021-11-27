import collections
import os
import pickle
import sys
import threading
import time
from types import FrameType
from typing import IO, Any, Dict, List, NewType, Optional

import greenlet
import objgraph
import psutil

from .constants import INTERVAL_SECONDS, MEGA
from .timer import TIMER, TIMER_SIGNAL, Timer

# Improvements:
# - The objcount itself is not that useful, add the _sys.getsizeof_ to know the
#   amount of memory used by the type (heapy is a good alternative for this)
# - Experiment with heapy or PySizer for memory profiling / leak hunting

FlameStack = NewType("FlameStack", str)
FlameGraph = Dict[FlameStack, int]


def frame_format(frame: FrameType) -> str:
    block_name = frame.f_code.co_name
    module_name = frame.f_globals.get("__name__")
    return "{}({})".format(block_name, module_name)


def collect_frames(frame: FrameType) -> List[str]:
    callstack = []
    optional_frame: Optional[FrameType] = frame
    while optional_frame is not None:
        callstack.append(frame_format(optional_frame))
        optional_frame = optional_frame.f_back

    callstack.reverse()
    return callstack


def flamegraph_format(stack_count: FlameGraph) -> str:
    return "\n".join("%s %d" % (key, value) for key, value in sorted(stack_count.items()))


def sample_stack(stack_count: FlameGraph, frame: FrameType, timespent) -> None:
    callstack = collect_frames(frame)

    formatted_stack = FlameStack(";".join(callstack))
    stack_count[formatted_stack] += timespent


def process_memory_mb(pid: int) -> float:
    process = psutil.Process(pid)
    memory = process.memory_info()[0]
    for child in process.children(recursive=True):
        memory += child.memory_info()[0]
    return memory / MEGA


def sample_memory(timestamp: float, pid: int, stream: IO) -> None:
    memory = process_memory_mb(pid)
    stream.write("{timestamp:.6f} {memory:.4f}\n".format(timestamp=timestamp, memory=memory))


def sample_objects(timestamp: float, stream: IO) -> None:
    # instead of keeping the count_per_type in memory, stream the data to a file
    # to save memory
    count_per_type: Dict[str, int] = objgraph.typestats()

    # add the timestamp for plotting
    data = [timestamp, count_per_type]

    data_pickled = pickle.dumps(data)
    stream.write(data_pickled)


class FlameGraphCollector:
    last_timestamp: Optional[float]

    def __init__(self, stack_stream: IO) -> None:
        self.stack_stream = stack_stream
        self.stack_count: FlameGraph = collections.defaultdict(int)

        # Correct the flamegraph proportionally to the time spent in the
        # function call. This is important for functions which are considerably
        # slower then the others.
        #
        # Because from whithin the interpreter it's not possible to execute a
        # function on stable intervals, the count of stacks does not correspond
        # to actual wall time. This is true even if posix signals are used. For
        # this reason the code has to account for the time spent between two
        # samples, otherwise functions which are called more frequently will
        # appear to take more of the cpu time.
        self.last_timestamp = None

    def collect(self, frame: FrameType, timestamp: float) -> None:
        if self.last_timestamp is not None:
            sample_stack(self.stack_count, frame, timestamp)

        self.last_timestamp = timestamp

    def stop(self) -> None:
        stack_data = flamegraph_format(self.stack_count)

        self.stack_stream.write(stack_data)
        self.stack_stream.close()

        del self.stack_stream
        del self.last_timestamp


class MemoryCollector:
    def __init__(self, memory_stream: IO) -> None:
        self.memory_stream = memory_stream

    def collect(self, _frame: FrameType, timestamp: float) -> None:
        # waiting for the cache to fill takes too long, just flush the data
        sample_memory(timestamp, os.getpid(), self.memory_stream)
        self.memory_stream.flush()

    def stop(self) -> None:
        self.memory_stream.close()
        del self.memory_stream


class ObjectCollector:
    def __init__(self, objects_stream: IO):
        self.objects_stream = objects_stream

    def collect(self, _frame: FrameType, timestamp: float) -> None:
        sample_objects(timestamp, self.objects_stream)
        self.objects_stream.flush()

    def stop(self) -> None:
        self.objects_stream.close()
        del self.objects_stream


class TraceSampler:
    old_frame: Optional[FrameType]

    def __init__(self, collector, sample_interval=0.1):
        self.collector = collector
        self.sample_interval = sample_interval
        self.last_timestamp = time.time()

        # Save the old frame to have proper stack reporting. If the following
        # code is executed:
        #
        #   slow() # At this point a new sample is *not* needed
        #   f2()   # When this calls happens a new sample is needed, *because
        #          # of the previous function*
        #
        # The above gets worse because a context switch can happen after the
        # call to slow, if this is not taken into account a completely wrong
        # stack trace will be reported.
        self.old_frame = None

        self.previous_callback = greenlet.gettrace()
        greenlet.settrace(self._greenlet_profiler)  # pylint: disable=c-extension-no-member
        sys.setprofile(self._thread_profiler)
        # threading.setprofile(self._thread_profiler)

    def _should_sample(self, timestamp: float) -> bool:
        if timestamp - self.last_timestamp >= self.sample_interval:
            self.last_timestamp = timestamp
            return True
        return False

    def _greenlet_profiler(self, event: str, args: Any) -> None:
        timestamp = time.time()
        try:
            # we need to account the time for the user function
            frame = sys._getframe(1)  # pylint:disable=protected-access
        except ValueError:
            # the first greenlet.switch() and when the greenlet is being
            # destroyed there is nothing more in the stack, so this function is
            # the first function called
            frame = sys._getframe(0)  # pylint:disable=protected-access

        if self._should_sample(timestamp):
            self.collector.collect(self.old_frame, timestamp)

        self.old_frame = frame

        if self.previous_callback is not None:
            return self.previous_callback(event, args)

        return None

    def _thread_profiler(self, frame: FrameType, _event: str, _arg: Any) -> None:
        timestamp = time.time()
        if self._should_sample(timestamp):
            self.collector.collect(self.old_frame, timestamp)
        self.old_frame = frame

    def stop(self) -> None:
        # Unregister the profiler in this order, otherwise we will have extra
        # measurements in the end
        sys.setprofile(None)
        threading.setprofile(None)
        greenlet.settrace(self.previous_callback)  # pylint: disable=c-extension-no-member

        self.collector.stop()
        self.collector = None


class SignalSampler:
    """Signal based sampler."""

    def __init__(
        self,
        collector,
        timer: int = TIMER,
        interval: float = INTERVAL_SECONDS,
        timer_signal: int = TIMER_SIGNAL,
    ) -> None:

        self.collector = collector
        # The timer must be started after collector is set
        self.timer = Timer(
            callback=self._timer_callback,
            timer=timer,
            interval=interval,
            timer_signal=timer_signal,
        )

    def _timer_callback(
        self, signum: int, frame: FrameType  # pylint: disable=unused-argument
    ) -> None:
        # Sample can be called one last time after sample_stop
        if self.collector is not None:
            self.collector.collect(frame, time.time())

    def stop(self) -> None:
        timer = self.timer
        collector = self.collector

        del self.timer
        del self.collector

        # The timer must be stoped before sampler
        timer.stop()
        collector.stop()
