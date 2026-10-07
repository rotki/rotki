import json
import logging
import threading
from collections import OrderedDict, deque
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Any, ClassVar, Final

from rotkehlchen.api.websockets.typedefs import (
    Delivery,
    DeliveryPolicy,
    UserMessageEntry,
    UserMessageFeature,
    UserMessageKey,
    UserMessageOperation,
    UserMessageRecord,
    WSMessageType,
    delivery_of,
)
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.api.websockets.notifier import RotkiNotifier
    from rotkehlchen.types import ExternalService, Location, Timestamp


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
# How many undelivered messages each store holds. Nothing drains them until a client
# connects or polls, and a logged in backend can run its periodic tasks for days with no
# browser open. A full store drops its oldest entry and counts the drop. The sum bounds
# what one poll hands the frontend to parse, and the frontend keeps 200 notifications,
# so more reports than that could not be shown anyway.
MAX_HELD_EVENTS: Final = 500
MAX_HELD_STATES: Final = 200
MAX_HELD_REPORTS: Final = 200
# User messages are reports too, but held in a store of their own with this limit, so a
# storm of distinct problems cannot push the structured reports out
MAX_HELD_USER_MESSAGES: Final = 200
# The interpolated values of a user message, unrendered. Kept to primitives because the
# payload goes through process_result and then json.dumps: a value neither can handle is
# logged and the message dropped rather than raised to the emitter, so it fails silently.
UserMessageField = str | int | float | bool | None
# The AuthFailure service for rotki's own premium credentials, shared so its emitters group
ROTKI_PREMIUM_SERVICE: Final = 'rotki_premium'


@dataclass(frozen=True)
class HeldMessage:
    """A message no client received, held until one connects or polls.

    `payload` is the `{type, data}` object the websocket sends. `text` is what tests and
    tools read: the rendered sentence of a user message, or the serialized payload. `count`
    is how many times it was sent while held and `last_sent` when it was last sent, since a
    client that reads it hours later cannot tell otherwise. For a message handed back by a
    client that disconnected before reading it, `last_sent` is when it was handed back,
    later than the send by at most that client's backlog. `seq` orders messages across
    the stores.
    """
    payload: dict[str, Any]
    text: str
    count: int
    last_sent: Timestamp
    seq: int

    def serialize(self) -> dict[str, Any]:
        return self.payload | {'count': self.count, 'last_sent': self.last_sent}


@dataclass(frozen=True)
class MessageClassification:
    """Why a user message happened, carrying the data its family cannot do without.

    A family is a dataclass rather than a bare enum member so that its required data is
    required at the call site. A BAD_DATA message with no `record` would collapse a failed
    trade and a failed balance into the same row, and nothing downstream could separate
    them again; here that message cannot be constructed at all.

    Subclasses hold only primitives, so the whole payload stays serializable, and only
    fields worth grouping or reading: the rendered sentence is already in `value`.

    `group_by` names the fields that, with the verbosity, family and subject, identify one
    problem. It is the only definition of a message's identity: the backend holds repeats
    under it and the frontend folds them into one row by it. The free-text `error` never
    takes part, since it varies between repeats of the same failure.
    """
    key: ClassVar[UserMessageKey]
    group_by: ClassVar[tuple[str, ...]]

    def serialize(self) -> dict[str, UserMessageField]:
        return {field.name: getattr(self, field.name) for field in fields(self)}

    def identity(self) -> list[UserMessageField]:
        return [getattr(self, field) for field in self.group_by]


@dataclass(frozen=True)
class BadData(MessageClassification):
    """A remote sent something we could not read.

    `record` is what was being read, and is what keeps two different storms from folding
    into one row.
    """
    key: ClassVar = UserMessageKey.BAD_DATA
    group_by: ClassVar = ('record',)
    record: UserMessageRecord
    error: str


@dataclass(frozen=True)
class NetworkFailure(MessageClassification):
    """A remote could not be reached, or refused the request.

    `record` is what was being queried, from the same vocabulary as BadData, so a failed
    trade query and an unreadable trade name the same thing.
    """
    key: ClassVar = UserMessageKey.NETWORK
    group_by: ClassVar = ('record',)
    record: UserMessageRecord
    error: str


@dataclass(frozen=True)
class AuthFailure(MessageClassification):
    """Credentials are missing, rejected or expired.

    Only the user can resolve this, so it groups per account: folding accounts together
    would hide which key needs replacing. Prefer WSMessageType.MISSING_API_KEY where it
    fits: it is already structured and already has a frontend handler.

    `service` is a fixed id (an exchange's location, ROTKI_PREMIUM_SERVICE, an
    ExternalService), never a name the user chose, so two services cannot collide.
    `account` is the user's name for the rejected account, when there can be several.
    """
    key: ClassVar = UserMessageKey.AUTH
    group_by: ClassVar = ('service', 'account')
    service: str
    account: str | None


@dataclass(frozen=True)
class UnknownAssetSeen(MessageClassification):
    """An asset rotki does not know about.

    Prefer WSMessageType.EXCHANGE_UNKNOWN_ASSET for an exchange symbol the user can map;
    ExchangeInterface.send_unknown_asset_message already fills in the location and name.
    An exchange's internal id that no symbol stands for (bitpanda's numeric ids) cannot be
    mapped, so it stays here with the id as `identifier`.
    """
    key: ClassVar = UserMessageKey.UNKNOWN_ASSET
    group_by: ClassVar = ('identifier',)
    identifier: str


@dataclass(frozen=True)
class LocalDbProblem(MessageClassification):
    """Our own stored data is inconsistent, or could not be written."""
    key: ClassVar = UserMessageKey.LOCAL_DB
    group_by: ClassVar = ('entry',)
    entry: UserMessageEntry


@dataclass(frozen=True)
class MissingPrice(MessageClassification):
    """No price could be found for an asset at a point in time.

    `asset` is null when a lookup for a batch of assets failed as a whole, and `timestamp`
    is null for a current price.
    """
    key: ClassVar = UserMessageKey.PRICE
    group_by: ClassVar = ()  # per location: one row for every price a location lacks
    asset: str | None
    timestamp: int | None


@dataclass(frozen=True)
class Unsupported(MessageClassification):
    """rotki does not support this thing yet."""
    key: ClassVar = UserMessageKey.UNSUPPORTED
    group_by: ClassVar = ('feature',)
    feature: UserMessageFeature


@dataclass(frozen=True)
class Internal(MessageClassification):
    """An invariant broke. The user can only file a report.

    `operation` is what keeps unrelated breakages apart: with no fields, every INTERNAL
    message would share one row.
    """
    key: ClassVar = UserMessageKey.INTERNAL
    group_by: ClassVar = ('operation',)
    operation: UserMessageOperation


class MessagesAggregator:
    """
    This class is passed around where needed and aggregates messages for the user
    """

    def __init__(self) -> None:
        # Messages are added from any worker thread and drained by the api or at logout
        self._lock = threading.Lock()
        self._seq = 0
        self._events: deque[HeldMessage] = deque()
        self._states: OrderedDict[str, HeldMessage] = OrderedDict()
        self._reports: OrderedDict[str, HeldMessage] = OrderedDict()
        self._user_messages: OrderedDict[str, HeldMessage] = OrderedDict()
        self._dropped = 0
        self.rotki_notifier: RotkiNotifier | None = None

    @staticmethod
    def _user_message_data(
            verbosity: str,
            msg: str,
            classification: MessageClassification,
            subject: Location | None,
    ) -> dict[str, Any]:
        """Assemble the USER_MESSAGE websocket payload.

        The key and the fields come from one object so they cannot disagree: a family and
        the data that family promises travel together or not at all. `subject` is null for
        a message that is not about any one location, such as a broken local database row.
        `group` is the message's identity, see MessageClassification.
        """
        serialized_subject = subject.serialize() if subject is not None else None
        return {
            'verbosity': verbosity,
            'value': msg,
            'key': classification.key,
            'subject': serialized_subject,
            'fields': classification.serialize(),
            'group': [
                verbosity,
                classification.key,
                serialized_subject,
                *classification.identity(),
            ],
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

    def _hold(self, envelope: dict[str, Any], delivery: Delivery) -> None:
        """Keep a message no client received, as its delivery policy says.

        A full store drops its oldest entry, so one kind of message can only ever crowd out
        its own kind: a storm of repeating failures cannot push out an event. A dropped
        message is logged in full, since the client is only told how many there were.
        """
        is_user_message = envelope['type'] == WSMessageType.USER_MESSAGE
        is_event = delivery.policy == DeliveryPolicy.EVENT
        try:
            text = envelope['data']['value'] if is_user_message else json.dumps(envelope)
            key = None if is_event else self._key(envelope, delivery)
        except TypeError as e:  # a bad value is the emitter's bug, not a reason to fail it
            log.error(
                'Could not hold a %s message that does not serialize: %s',
                envelope['type'],
                e,
            )
            return

        now = ts_now()
        dropped: HeldMessage | None = None
        with self._lock:
            self._seq += 1
            if delivery.policy == DeliveryPolicy.EVENT:
                self._events.append(HeldMessage(
                    payload=envelope,
                    text=text,
                    count=1,
                    last_sent=now,
                    seq=self._seq,
                ))
                if len(self._events) > MAX_HELD_EVENTS:
                    dropped = self._events.popleft()
                    self._dropped += 1
            else:
                assert key is not None, 'only an EVENT is held without a key'
                dropped = self._hold_keyed(
                    envelope=envelope,
                    text=text,
                    key=key,
                    store_limit=self._store_of(delivery.policy, is_user_message),
                    now=now,
                )

        if dropped is not None:
            log.warning(
                'Dropped a held %s message sent %d time(s), last at %d, to stay within '
                'the held message limits: %s',
                dropped.payload['type'],
                dropped.count,
                dropped.last_sent,
                dropped.text,
            )

    @staticmethod
    def _key(envelope: dict[str, Any], delivery: Delivery) -> str:
        """The key two messages share when the later one replaces or repeats the earlier."""
        data = envelope['data']
        identity = data if delivery.whole_payload else [
            data.get(field) for field in delivery.key_fields
        ]
        return json.dumps([envelope['type'], identity], sort_keys=True)

    def _store_of(
            self,
            policy: DeliveryPolicy,
            is_user_message: bool,
    ) -> tuple[OrderedDict[str, HeldMessage], int]:
        if policy == DeliveryPolicy.STATE:
            return self._states, MAX_HELD_STATES
        if is_user_message:
            return self._user_messages, MAX_HELD_USER_MESSAGES
        return self._reports, MAX_HELD_REPORTS

    def _hold_keyed(
            self,
            envelope: dict[str, Any],
            text: str,
            key: str,
            store_limit: tuple[OrderedDict[str, HeldMessage], int],
            now: Timestamp,
    ) -> HeldMessage | None:
        """Keep a keyed message, replacing an earlier one with the same key.

        Must be called with the lock held. Returns the entry dropped to make room, if any.
        """
        store, limit = store_limit
        previous = store.pop(key, None)
        store[key] = HeldMessage(
            payload=envelope,
            text=text,
            count=1 if previous is None else previous.count + 1,
            last_sent=now,
            seq=self._seq,
        )
        if len(store) <= limit:
            return None

        self._dropped += 1
        return store.popitem(last=False)[1]

    def _hold_message(
            self,
            message_type: WSMessageType,
            data: dict[str, Any] | list[Any],
    ) -> None:
        if (delivery := delivery_of(message_type, data)).policy != DeliveryPolicy.LIVE:
            self._hold(envelope=self._envelope(message_type, data), delivery=delivery)

    def _drain_locked(self, select: Callable[[HeldMessage], bool]) -> list[HeldMessage]:
        """Remove the held messages `select` picks, in the order they were last sent.

        Must be called with the lock held.
        """
        drained = [message for message in self._events if select(message)]
        self._events = deque(message for message in self._events if not select(message))
        for store in (self._states, self._reports, self._user_messages):
            selected = [key for key, message in store.items() if select(message)]
            drained.extend(store.pop(key) for key in selected)
        return sorted(drained, key=lambda message: message.seq)

    def add_warning(
            self,
            msg: str,
            *,
            classification: MessageClassification,
            subject: Location | None = None,
    ) -> None:
        log.warning(msg)
        self.add_message(
            message_type=WSMessageType.USER_MESSAGE,
            data=self._user_message_data(
                verbosity='warning',
                msg=msg,
                classification=classification,
                subject=subject,
            ),
        )

    def add_error(
            self,
            msg: str,
            *,
            classification: MessageClassification,
            subject: Location | None = None,
    ) -> None:
        log.error(msg)
        self.add_message(
            message_type=WSMessageType.USER_MESSAGE,
            data=self._user_message_data(
                verbosity='error',
                msg=msg,
                classification=classification,
                subject=subject,
            ),
        )

    def add_message(
            self,
            message_type: WSMessageType,
            data: dict[str, Any] | list[Any],
    ) -> None:
        """Send a websocket message, or hold it for the next client if none receives it."""
        if self.rotki_notifier is None:
            self._hold_message(message_type=message_type, data=data)
            return

        self.rotki_notifier.broadcast(
            message_type=message_type,
            to_send_data=data,
            failure_callback=self._hold_message,
            failure_callback_args={'message_type': message_type, 'data': data},
        )

    def requeue_undelivered(self, raw_message: str) -> None:
        """Hold a message that was queued to a websocket client which disconnected before
        receiving it, as if its send had failed outright."""
        try:
            message = json.loads(raw_message)
            message_type = WSMessageType(message['type'])
        except (json.JSONDecodeError, KeyError, ValueError):
            log.error('Could not parse undelivered websocket message %s', raw_message)
            return

        if (delivery := delivery_of(message_type, message['data'])).policy != DeliveryPolicy.LIVE:
            self._hold(envelope=message, delivery=delivery)

    def consume_held(self) -> tuple[list[dict[str, Any]], int]:
        """Drain every held message for a client, with how many were dropped for room.

        Each message is the `{type, data}` object the websocket sends plus its `count`.
        The drain and the drop counter are read under one lock, so a message dropped
        between them cannot be counted against the wrong poll.
        """
        with self._lock:
            held = self._drain_locked(lambda _: True)
            dropped, self._dropped = self._dropped, 0
        return [message.serialize() for message in held], dropped

    def clear(self) -> None:
        """Drop every held message, so none leaks into the next user's session."""
        with self._lock:
            self._drain_locked(lambda _: True)
            self._dropped = 0

    def add_missing_key_message(
            self,
            service: ExternalService,
            location: str | None = None,
            reason: str | None = None,
    ) -> None:
        """Send an API key problem for the specified service unless its messages are suppressed.

        ``reason`` distinguishes a missing credential from a configured credential that the
        service rejected, while keeping both cases on the existing websocket message type.
        """
        if service in CachedSettings().get_settings().suppress_missing_key_msg_services:
            return

        data = {'service': service.serialize()}
        if location is not None:
            data['location'] = location
        if reason is not None:
            data['reason'] = reason

        self.add_message(message_type=WSMessageType.MISSING_API_KEY, data=data)

    @staticmethod
    def how_many_events_per_ws(total_events: int) -> int:
        """
        Scales the number of events needed to send a WS message. Start from 5 and scale up to 50
        linearly if total events >= 1000.
        """
        return min(50, max(5, 5 + max(0, total_events - 50) // 20))
