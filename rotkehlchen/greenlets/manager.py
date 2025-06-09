# TODO: Replace with AsyncTaskManager when migrating to asyncio
import logging
import traceback
from collections.abc import Callable
from typing import Any

import gevent

from rotkehlchen.errors.misc import GreenletKilledError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GreenletManager:
    """A class to collect and manage greenlets spawned by various sources"""

    def __init__(self, msg_aggregator: MessagesAggregator) -> None:
        self.msg_aggregator = msg_aggregator
        self.greenlets: list[gevent.Greenlet] = []

    def add(self, task_name: str, greenlet: gevent.Greenlet, exception_is_error: bool) -> None:
        greenlet.link_exception(self._handle_killed_greenlets)
        greenlet.task_name = task_name
        greenlet.exception_is_error = exception_is_error
        self.greenlets.append(greenlet)

    def clear(self) -> None:
        """Clears all tracked greenlets. To be called when logging out or shutting down"""
        gevent.killall(self.greenlets)
        self.greenlets.clear()

    def clear_finished(self) -> None:
        """Remove all finished tracked greenlets from the list"""
        self.greenlets = [x for x in self.greenlets if not x.dead]

    def spawn_and_track(
            self,
            after_seconds: float | None,
            task_name: str,
            exception_is_error: bool,
            method: Callable,
            **kwargs: Any,
    ) -> gevent.Greenlet:
        log.debug(f'Spawning task manager task "{task_name}"')
        if after_seconds is None:
            greenlet = gevent.spawn(method, **kwargs)
        else:
            greenlet = gevent.spawn_later(after_seconds, method, **kwargs)
        self.add(task_name, greenlet, exception_is_error)
        return greenlet

    def has_task(self, name: str) -> bool:
        """Check if there is a running task with the given name"""
        for greenlet in self.greenlets:
            if greenlet.dead is False and greenlet.task_name.startswith(name):
                return True

        return False

    def _handle_killed_greenlets(self, greenlet: gevent.Greenlet) -> None:
        if not greenlet.exception:
            log.error('went in handle_killed_greenlets without an exception')
            return

        task_name = getattr(greenlet, 'task_name', 'Unknown task')
        if isinstance(greenlet.exception, GreenletKilledError):
            log.debug(f'Greenlet for task {task_name} was killed')
            return

        exception_is_error = getattr(greenlet, 'exception_is_error', True)
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
