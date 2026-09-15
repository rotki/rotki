import json
import logging
from collections import deque
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Any, ClassVar

from rotkehlchen.api.websockets.typedefs import UserMessageKey, UserMessageRecord, WSMessageType
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.api.websockets.notifier import RotkiNotifier
    from rotkehlchen.types import ExternalService, Location


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
ERROR_MESSAGE_TYPES = {WSMessageType.USER_MESSAGE, WSMessageType.BALANCE_SNAPSHOT_ERROR}
# The interpolated values of a user message, unrendered. Kept to primitives because the
# payload goes through process_result and then json.dumps: a value neither can handle makes
# broadcast log and fall back to polling instead of raising, so it would fail silently.
UserMessageField = str | int | float | bool | None


@dataclass(frozen=True)
class PolledMessage:
    """A message held for the polling fallback, in both forms it is read in.

    `text` is what tests, tools and logout read: the rendered sentence of a user message, or
    the serialized envelope of a structured one. `payload` is what the messages endpoint
    returns, the same `{type, data}` object the websocket sends, and the only form in which a
    user message keeps its classification once the socket is gone.
    """
    text: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class MessageClassification:
    """Why a user message happened, carrying the data its family cannot do without.

    A family is a dataclass rather than a bare enum member so that its required data is
    required at the call site. A BAD_DATA message with no `record` would collapse a failed
    trade and a failed balance into the same row, and nothing downstream could separate
    them again; here that message cannot be constructed at all.

    Subclasses hold only primitives, so the whole payload stays serializable, and only
    fields worth grouping or reading: the rendered sentence is already in `value`.
    """
    key: ClassVar[UserMessageKey]

    def serialize(self) -> dict[str, UserMessageField]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True)
class BadData(MessageClassification):
    """A remote sent something we could not read.

    `record` is what was being read, and is what keeps two different storms from folding
    into one row.
    """
    key: ClassVar = UserMessageKey.BAD_DATA
    record: UserMessageRecord
    error: str


@dataclass(frozen=True)
class NetworkFailure(MessageClassification):
    """A remote could not be reached, or refused the request.

    `record` is what was being queried, from the same vocabulary as BadData, so a failed
    trade query and an unreadable trade name the same thing.
    """
    key: ClassVar = UserMessageKey.NETWORK
    record: UserMessageRecord
    error: str


@dataclass(frozen=True)
class AuthFailure(MessageClassification):
    """Credentials are missing, rejected or expired.

    Only the user can resolve this, so it is the one family that must not collapse into a
    count. Prefer WSMessageType.MISSING_API_KEY where it fits: it is already structured
    and already has a frontend handler.
    """
    key: ClassVar = UserMessageKey.AUTH
    service: str


@dataclass(frozen=True)
class UnknownAssetSeen(MessageClassification):
    """An asset rotki does not know about.

    Prefer WSMessageType.EXCHANGE_UNKNOWN_ASSET on an exchange; ExchangeInterface.
    send_unknown_asset_message already fills in the location and name.
    """
    key: ClassVar = UserMessageKey.UNKNOWN_ASSET
    identifier: str


@dataclass(frozen=True)
class LocalDbProblem(MessageClassification):
    """Our own stored data is inconsistent, or could not be written."""
    key: ClassVar = UserMessageKey.LOCAL_DB
    entry: str


@dataclass(frozen=True)
class MissingPrice(MessageClassification):
    """No price could be found for an asset at a point in time."""
    key: ClassVar = UserMessageKey.PRICE
    asset: str
    timestamp: int | None


@dataclass(frozen=True)
class Unsupported(MessageClassification):
    """rotki does not support this thing yet."""
    key: ClassVar = UserMessageKey.UNSUPPORTED
    feature: str


@dataclass(frozen=True)
class Internal(MessageClassification):
    """An invariant broke. The user can only file a report, so this never collapses."""
    key: ClassVar = UserMessageKey.INTERNAL


class MessagesAggregator:
    """
    This class is passed around where needed and aggregates messages for the user
    """

    def __init__(self) -> None:
        self.warnings: deque[PolledMessage] = deque()
        self.errors: deque[PolledMessage] = deque()
        self.rotki_notifier: RotkiNotifier | None = None

    @staticmethod
    def _user_message_data(
            verbosity: str,
            msg: str,
            classification: MessageClassification | None,
            subject: Location | None,
    ) -> dict[str, Any]:
        """Assemble the USER_MESSAGE websocket payload.

        key/subject/fields are always present, null when the emitter did not classify
        itself. Omitting them instead would make an unclassified message indistinguishable
        on the wire from one predating this field, which is the state that let 187 emitters
        stay unidentifiable in the first place. A null here is visible in any capture.

        The key and the fields come from one object so they cannot disagree: a family and
        the data that family promises travel together or not at all.
        """
        return {
            'verbosity': verbosity,
            'value': msg,
            'key': classification.key if classification is not None else None,
            'subject': subject.serialize() if subject is not None else None,
            'fields': classification.serialize() if classification is not None else None,
        }

    @staticmethod
    def _envelope(
            message_type: WSMessageType,
            data: dict[str, Any] | list[Any],
    ) -> dict[str, Any]:
        """Build a message the way broadcast sends it, for the polling fallback.

        process_result is imported here and not at module level because serialize imports
        exchange modules, and those import the classification families from this module.
        """
        from rotkehlchen.serialization.serialize import process_result
        return process_result({'type': message_type, 'data': data})

    @classmethod
    def _user_message_polled(cls, msg: str, data: dict[str, Any]) -> PolledMessage:
        return PolledMessage(text=msg, payload=cls._envelope(WSMessageType.USER_MESSAGE, data))

    @staticmethod
    def _drain(messages: deque[PolledMessage]) -> list[PolledMessage]:
        result = []
        while True:
            try:
                result.append(messages.pop())
            except IndexError:  # a concurrent consumer (api call/logout) drained it
                return result

    def _append_warning(self, msg: str, data: dict[str, Any]) -> None:
        self.warnings.appendleft(self._user_message_polled(msg=msg, data=data))

    def add_warning(
            self,
            msg: str,
            *,
            classification: MessageClassification | None = None,
            subject: Location | None = None,
    ) -> None:
        log.warning(msg)
        data = self._user_message_data(
            verbosity='warning',
            msg=msg,
            classification=classification,
            subject=subject,
        )
        if self.rotki_notifier is not None:
            self.rotki_notifier.broadcast(
                message_type=WSMessageType.USER_MESSAGE,
                to_send_data=data,
                failure_callback=self._append_warning,
                failure_callback_args={'msg': msg, 'data': data},
            )
            return
        # else
        self._append_warning(msg=msg, data=data)

    def consume_warnings(self) -> list[str]:
        """Drain the pending warnings as rendered text."""
        return [message.text for message in self._drain(self.warnings)]

    def consume_warning_payloads(self) -> list[dict[str, Any]]:
        """Drain the pending warnings as the `{type, data}` objects the websocket sends."""
        return [message.payload for message in self._drain(self.warnings)]

    def _append_error(self, msg: str, data: dict[str, Any]) -> None:
        self.errors.appendleft(self._user_message_polled(msg=msg, data=data))

    def _append_structured_error(self, envelope: dict[str, Any]) -> None:
        self.errors.appendleft(PolledMessage(text=json.dumps(envelope), payload=envelope))

    def add_error(
            self,
            msg: str,
            *,
            classification: MessageClassification | None = None,
            subject: Location | None = None,
    ) -> None:
        log.error(msg)
        data = self._user_message_data(
            verbosity='error',
            msg=msg,
            classification=classification,
            subject=subject,
        )
        if self.rotki_notifier is not None:
            self.rotki_notifier.broadcast(
                message_type=WSMessageType.USER_MESSAGE,
                to_send_data=data,
                failure_callback=self._append_error,
                failure_callback_args={'msg': msg, 'data': data},
            )
            return
        self._append_error(msg=msg, data=data)

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
        envelope = self._envelope(message_type, data)
        # Only error-class messages fall back to polling, whichever way delivery failed
        is_error = message_type in ERROR_MESSAGE_TYPES

        if self.rotki_notifier is not None:
            self.rotki_notifier.broadcast(
                message_type=message_type,
                to_send_data=data,
                failure_callback=self._append_structured_error if is_error else None,
                failure_callback_args={'envelope': envelope},
            )

        elif is_error:
            self._append_structured_error(envelope)

    def requeue_undelivered(self, raw_message: str) -> None:
        """Callback for a message that was queued to a websocket client which
        disconnected before receiving it. Re-queues error-class messages into
        the polling fallback deques, mirroring what the failure callbacks of
        add_warning/add_error/add_message do when a send fails outright.
        Everything else (progress updates etc.) is dropped, as it is only
        meaningful to a connected client."""
        try:
            message = json.loads(raw_message)
        except json.JSONDecodeError:
            log.error('Could not parse undelivered websocket message %s', raw_message)
            return

        if (msg_type := message.get('type')) == WSMessageType.USER_MESSAGE:
            data = message.get('data', {})
            if (value := data.get('value')) is None:
                return
            polled = PolledMessage(text=value, payload=message)
            if data.get('verbosity') == 'warning':
                self.warnings.appendleft(polled)
            else:
                self.errors.appendleft(polled)
        elif msg_type in ERROR_MESSAGE_TYPES:
            self._append_structured_error(message)

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
        """Drain the pending errors as rendered text."""
        return [message.text for message in self._drain(self.errors)]

    def consume_error_payloads(self) -> list[dict[str, Any]]:
        """Drain the pending errors as the `{type, data}` objects the websocket sends."""
        return [message.payload for message in self._drain(self.errors)]

    @staticmethod
    def how_many_events_per_ws(total_events: int) -> int:
        """
        Scales the number of events needed to send a WS message. Start from 5 and scale up to 50
        linearly if total events >= 1000.
        """
        return min(50, max(5, 5 + max(0, total_events - 50) // 20))
