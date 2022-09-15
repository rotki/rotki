import json
import logging
from collections import deque
from typing import TYPE_CHECKING, Any, Deque, Dict, List, Optional

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.api.websockets.notifier import RotkiNotifier


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
INFORMATIONAL_MESSAGE_TYPES = {
    WSMessageType.ETHEREUM_TRANSACTION_STATUS,
    WSMessageType.PREMIUM_STATUS_UPDATE,
}


class MessagesAggregator():
    """
    This class is passed around where needed and aggregates messages for the user
    """

    def __init__(self) -> None:
        self.warnings: Deque = deque()
        self.errors: Deque = deque()
        self.rotki_notifier: Optional['RotkiNotifier'] = None

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

    def consume_warnings(self) -> List[str]:
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
            data: Dict[str, Any],
    ) -> None:
        fallback_msg = json.dumps({'type': str(message_type), 'data': data})  # noqa: E501  # kind of silly to repeat it here. Same code in broadcast

        if self.rotki_notifier is not None:
            self.rotki_notifier.broadcast(
                message_type=message_type,
                to_send_data=data,
                failure_callback=self._append_error,
                failure_callback_args={'msg': fallback_msg},
            )
        else:
            # Avoid sending as error informational messages
            if message_type not in INFORMATIONAL_MESSAGE_TYPES:
                self.errors.appendleft(fallback_msg)

    def consume_errors(self) -> List[str]:
        result = []
        while len(self.errors) != 0:
            result.append(self.errors.pop())
        return result
