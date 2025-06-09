import asyncio
import json
import logging
from collections import deque
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.serialize import process_result

if TYPE_CHECKING:
    from rotkehlchen.api.websockets.notifier import RotkiNotifier


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
ERROR_MESSAGE_TYPES = {WSMessageType.LEGACY, WSMessageType.BALANCE_SNAPSHOT_ERROR}


class MessagesAggregator:
    """
    This class is passed around where needed and aggregates messages for the user
    """

    def __init__(self) -> None:
        self.warnings: deque = deque()
        self.errors: deque = deque()
        self.rotki_notifier: RotkiNotifier | None = None
    
    def _sync_broadcast(
            self,
            message_type: WSMessageType,
            to_send_data: dict[str, Any] | list[Any],
            success_callback: Callable | None = None,
            success_callback_args: dict[str, Any] | None = None,
            failure_callback: Callable | None = None,
            failure_callback_args: dict[str, Any] | None = None,
    ) -> None:
        """Helper to call async broadcast from sync context"""
        if self.rotki_notifier is None:
            return
            
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule the coroutine
                asyncio.create_task(
                    self.rotki_notifier.broadcast(
                        message_type=message_type,
                        to_send_data=to_send_data,
                        success_callback=success_callback,
                        success_callback_args=success_callback_args,
                        failure_callback=failure_callback,
                        failure_callback_args=failure_callback_args,
                    )
                )
            else:
                # Run in thread-safe manner
                asyncio.run_coroutine_threadsafe(
                    self.rotki_notifier.broadcast(
                        message_type=message_type,
                        to_send_data=to_send_data,
                        success_callback=success_callback,
                        success_callback_args=success_callback_args,
                        failure_callback=failure_callback,
                        failure_callback_args=failure_callback_args,
                    ),
                    loop
                )
        except RuntimeError:
            # No event loop - call failure callback
            if failure_callback:
                failure_callback_args = failure_callback_args or {}
                failure_callback(**failure_callback_args)

    def _append_warning(self, msg: str) -> None:
        self.warnings.appendleft(msg)

    def add_warning(self, msg: str) -> None:
        log.warning(msg)
        if self.rotki_notifier is not None:
            data = {'verbosity': 'warning', 'value': msg}
            self._sync_broadcast(
                message_type=WSMessageType.LEGACY,
                to_send_data=data,
                failure_callback=self._append_warning,
                failure_callback_args={'msg': msg},
            )
            return
        # else
        self.warnings.appendleft(msg)

    def consume_warnings(self) -> list[str]:
        result = []
        while len(self.warnings) != 0:
            result.append(self.warnings.pop())
        return result

    def _append_error(self, msg: str) -> None:
        self.errors.appendleft(msg)

    def add_error(self, msg: str) -> None:
        log.error(msg)
        if self.rotki_notifier is not None:
            data = {'verbosity': 'error', 'value': msg}
            self._sync_broadcast(
                message_type=WSMessageType.LEGACY,
                to_send_data=data,
                failure_callback=self._append_error,
                failure_callback_args={'msg': msg},
            )
            return
        self.errors.appendleft(msg)

    def add_message(
            self,
            message_type: WSMessageType,
            data: dict[str, Any] | list[Any],
    ) -> None:
        """Sends a websocket message

        Specify its type and data.

        Messages are sent asynchronously via asyncio tasks when an event loop is available.
        """
        fallback_msg = json.dumps(process_result({'type': message_type, 'data': data}))  # kind of silly to repeat it here. Same code in broadcast  # noqa: E501

        if self.rotki_notifier is not None:
            self._sync_broadcast(
                message_type=message_type,
                to_send_data=data,
                failure_callback=self._append_error,
                failure_callback_args={'msg': fallback_msg},
            )

        elif message_type in ERROR_MESSAGE_TYPES:  # Fallback to polling for error messages
            self.errors.appendleft(fallback_msg)

    def consume_errors(self) -> list[str]:
        result = []
        while len(self.errors) != 0:
            result.append(self.errors.pop())
        return result

    @staticmethod
    def how_many_events_per_ws(total_events: int) -> int:
        """
        Scales the number of events needed to send a WS message. Start from 5 and scale up to 50
        linearly if total events >= 1000.
        """
        return min(50, max(5, 5 + max(0, total_events - 50) // 20))
