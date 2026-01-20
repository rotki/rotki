import json
import logging
from collections import deque
from typing import TYPE_CHECKING, Any

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.serialize import process_result
from rotkehlchen.types import ExternalService

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

    def _append_warning(self, msg: str) -> None:
        self.warnings.appendleft(msg)

    def add_warning(self, msg: str) -> None:
        log.warning(msg)
        if self.rotki_notifier is not None:
            data = {'verbosity': 'warning', 'value': msg}
            self.rotki_notifier.broadcast(
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
            self.rotki_notifier.broadcast(
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

        `wait_on_send` is used to determine if the message should be sent asynchronously
        by spawning a greenlet or if it should just do it synchronously.
        """
        fallback_msg = json.dumps(process_result({'type': message_type, 'data': data}))  # kind of silly to repeat it here. Same code in broadcast  # noqa: E501

        if self.rotki_notifier is not None:
            self.rotki_notifier.broadcast(
                message_type=message_type,
                to_send_data=data,
                failure_callback=self._append_error,
                failure_callback_args={'msg': fallback_msg},
            )

        elif message_type in ERROR_MESSAGE_TYPES:  # Fallback to polling for error messages
            self.errors.appendleft(fallback_msg)

    def add_missing_key_message(
            self,
            service: ExternalService,
            location: str | None = None,
    ) -> None:
        """Send a missing key message for the specified service unless this service is marked
        to have its missing key messages suppressed.
        """
        if service in CachedSettings().get_settings().suppress_missing_key_msg_services:
            return

        data = {'service': service.serialize()}
        if location is not None:
            data['location'] = location

        self.add_message(message_type=WSMessageType.MISSING_API_KEY, data=data)

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
