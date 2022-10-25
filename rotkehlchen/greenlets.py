import logging
import traceback
from typing import Any, Callable, List, Optional

import gevent

from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GreenletManager():
    """A class to collect and manage greenlets spawned by various sources"""

    def __init__(self, msg_aggregator: MessagesAggregator) -> None:
        self.msg_aggregator = msg_aggregator
        self.greenlets: List[gevent.Greenlet] = []

    def add(self, task_name: str, greenlet: gevent.Greenlet, exception_is_error: bool) -> None:
        greenlet.link_exception(self._handle_killed_greenlets)
        greenlet.task_name = task_name
        greenlet.exception_is_error = exception_is_error
        self.greenlets.append(greenlet)

    def clear(self) -> None:
        """Clears all tracked greenlets. To be called when logging out or shutting down"""
        gevent.killall(self.greenlets)

    def clear_finished(self) -> None:
        """Remove all finished tracked greenlets from the list"""
        self.greenlets = [x for x in self.greenlets if not x.dead]

    def spawn_and_track(
            self,
            after_seconds: Optional[float],
            task_name: str,
            exception_is_error: bool,
            method: Callable,
            **kwargs: Any,
    ) -> gevent.Greenlet:
        if after_seconds is None:
            greenlet = gevent.spawn(method, **kwargs)
        else:
            greenlet = gevent.spawn_later(after_seconds, method, **kwargs)
        self.add(task_name, greenlet, exception_is_error)
        return greenlet

    def _handle_killed_greenlets(self, greenlet: gevent.Greenlet) -> None:
        if not greenlet.exception:
            log.error('went in handle_killed_greenlets without an exception')
            return

        exception_is_error = getattr(greenlet, 'exception_is_error', True)
        task_name = getattr(greenlet, 'task_name', 'Unknown task')
        first_line = f'{task_name} died with exception: {greenlet.exception}'
        if not exception_is_error:
            log.warning(f'{first_line} but that is not treated as an error')
            return

        msg = (
            f'{first_line}.\n'
            f'Exception Name: {greenlet.exc_info[0]}\nException Info: {greenlet.exc_info[1]}'
            f'\nTraceback:\n {"".join(traceback.format_tb(greenlet.exc_info[2]))}'
        )
        log.error(msg)
        self.msg_aggregator.add_error(f'{first_line}. Check the logs for more details')
