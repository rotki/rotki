import logging
from collections import deque
from typing import TYPE_CHECKING, Deque, List, Optional

from rotkehlchen.api.websockets.typedefs import WSMessageType

if TYPE_CHECKING:
    from rotkehlchen.api.websockets.notifier import RotkiNotifier


logger = logging.getLogger(__name__)


class MessagesAggregator():
    """
    This class is passed around where needed and aggreggates messages for the user
    """

    def __init__(self) -> None:
        self.warnings: Deque = deque()
        self.errors: Deque = deque()
        self.rotki_notifier: Optional['RotkiNotifier'] = None

    def _append_warning(self, msg: str) -> None:
        self.warnings.appendleft(msg)

    def add_warning(self, msg: str) -> None:
        logger.warning(msg)
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
        logger.error(msg)
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

    def consume_errors(self) -> List[str]:
        result = []
        while len(self.errors) != 0:
            result.append(self.errors.pop())
        return result
