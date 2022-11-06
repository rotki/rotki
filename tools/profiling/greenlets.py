import json
import sys
from datetime import datetime
from typing import Any

import greenlet
import structlog

from .sampler import collect_frames

log = structlog.get_logger(__name__)


def install_switch_log():
    # Do not overwrite the previous installed tracing function, this could be
    # another profiling tool, and if the callback is overwriten the tool would
    # not work as expected (e.g. a trace sampler)
    previous_callback = greenlet.gettrace()

    def log_every_switch(event: str, args: Any) -> None:
        if event == "switch":
            origin, target = args

            # Collecting the complete stack frame because the top-level
            # function will be a greenlet, and the bottom function may be an
            # external library. To understand what is going on the application
            # code, the whole stack is necessary.
            frame = sys._getframe(0)
            callstack = collect_frames(frame)

            # Using `print` because logging will not work here, the logger may
            # not be properly initialized on a fresh greenlet and will try to
            # use a nullable variable.
            print(
                json.dumps(
                    {
                        "event": "Switching",
                        "origin": str(origin),
                        "target": str(target),
                        "target_callstack": callstack,
                        "time": datetime.utcnow().isoformat(),
                    },
                ),
            )

        if previous_callback is not None:
            return previous_callback(event, args)

        return None

    greenlet.settrace(log_every_switch)

    return previous_callback


class SwitchMonitoring:
    def __init__(self) -> None:
        self.previous_callback = install_switch_log()

    def stop(self) -> None:
        # This is a best effort only. It is possible for another tracing function
        # to be installed after the `install_switch_log` is called, and this would
        # overwrite it.
        greenlet.settrace(self.previous_callback)
