import json
import logging
import threading
from collections import OrderedDict, deque
from dataclasses import dataclass, fields
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, ClassVar, Final, assert_never

from rotkehlchen.api.websockets.typedefs import (
    ProgressUpdateSubType,
    UserMessageEntry,
    UserMessageFeature,
    UserMessageKey,
    UserMessageOperation,
    UserMessageRecord,
    WSMessageType,
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
MAX_HELD_USER_MESSAGES: Final = 200
# The interpolated values of a user message, unrendered. Kept to primitives because the
# payload goes through process_result and then json.dumps: a value neither can handle is
# logged and the message dropped rather than raised to the emitter, so it fails silently.
UserMessageField = str | int | float | bool | None


class DeliveryPolicy(Enum):
    """What happens to a message no client received, decided by what losing it costs."""
    LIVE = auto()  # progress of work in flight, meaningless once it is over: dropped
    EVENT = auto()  # something that happened once: every one is held, in order
    STATE = auto()  # how things are now: only the latest per key is held
    REPORT = auto()  # a failure that tends to repeat: held once per key, with a count
    # a free-text user message: held like a REPORT, but in a store of its own, since text
    # that varies with every occurrence would otherwise push the structured reports out
    MESSAGE = auto()


@dataclass(frozen=True)
class Delivery:
    """How an undelivered message of one type is held.

    `key_fields` are the data fields that tell two STATE or REPORT messages of one type
    apart, and none means one entry for the whole type. `whole_payload` keys on every
    field instead, so only exact repeats collapse: a report whose text varies is still
    held once per distinct text, and never replaced by a different one.
    """
    policy: DeliveryPolicy
    key_fields: tuple[str, ...] = ()
    whole_payload: bool = False


LIVE: Final = Delivery(DeliveryPolicy.LIVE)
EVENT: Final = Delivery(DeliveryPolicy.EVENT)
LATEST: Final = Delivery(DeliveryPolicy.STATE)
EXACT_REPEATS: Final = Delivery(DeliveryPolicy.REPORT, whole_payload=True)


def delivery_of(message_type: WSMessageType, data: dict[str, Any] | list[Any]) -> Delivery:
    """Decide how an undelivered message is held until a client connects or polls.

    Every message type needs an answer, and assert_never makes a new one without an
    answer a type error rather than a message that silently falls back to a default.
    """
    match message_type:
        case (
            WSMessageType.TRANSACTION_STATUS |
            WSMessageType.DB_UPGRADE_STATUS |
            WSMessageType.DATA_MIGRATION_STATUS |
            WSMessageType.HISTORY_EVENTS_STATUS |
            WSMessageType.DATABASE_UPLOAD_PROGRESS
        ):
            return LIVE
        case WSMessageType.PROGRESS_UPDATES:  # a CSV import reports its outcome as its last frame
            is_import_result = (
                isinstance(data, dict) and
                data.get('subtype') == ProgressUpdateSubType.CSV_IMPORT_RESULT
            )
            return EVENT if is_import_result else LIVE
        case WSMessageType.NEW_TOKEN_DETECTED | WSMessageType.EVMLIKE_ACCOUNTS_DETECTION:
            return EVENT
        case (
            WSMessageType.PREMIUM_STATUS_UPDATE |
            WSMessageType.DATABASE_UPLOAD_RESULT |
            WSMessageType.GNOSISPAY_SESSIONKEY_EXPIRED |
            WSMessageType.MONERIUM_SESSIONKEY_EXPIRED |
            WSMessageType.ACCOUNTING_RULE_CONFLICT |
            WSMessageType.UNMATCHED_ASSET_MOVEMENTS |
            WSMessageType.UNMATCHED_BRIDGE_TRANSACTIONS |
            WSMessageType.INTERNAL_TX_FIXED |
            WSMessageType.SOLANA_TOKENS_MIGRATION |
            WSMessageType.HISTORICAL_BALANCE_PROCESSING_COMPLETED
        ):
            return LATEST
        case WSMessageType.REFRESH_BALANCES:
            return Delivery(DeliveryPolicy.STATE, key_fields=('blockchain',))
        case WSMessageType.NO_AVAILABLE_INDEXERS:
            return Delivery(DeliveryPolicy.STATE, key_fields=('chain',))
        case WSMessageType.MISSING_API_KEY:
            return Delivery(DeliveryPolicy.STATE, key_fields=('service', 'location'))
        case WSMessageType.CALENDAR_REMINDER:  # re-sent every few minutes until acknowledged
            return Delivery(DeliveryPolicy.STATE, key_fields=('identifier',))
        case WSMessageType.NEGATIVE_BALANCE_DETECTED:
            return Delivery(DeliveryPolicy.STATE, key_fields=('event_identifier',))
        case WSMessageType.USER_MESSAGE:
            # rejected credentials are the one family only the user can fix, and there
            # is one per account, so they are kept as state no storm of other text can evict
            is_auth = isinstance(data, dict) and data.get('key') == UserMessageKey.AUTH
            return Delivery(
                DeliveryPolicy.STATE if is_auth else DeliveryPolicy.MESSAGE,
                whole_payload=True,
            )
        case WSMessageType.BALANCE_SNAPSHOT_ERROR:
            return EXACT_REPEATS
        case WSMessageType.BINANCE_PAIRS_MISSING:
            return Delivery(DeliveryPolicy.REPORT, key_fields=('location', 'name'))
        case WSMessageType.ORACLE_PENALIZED:
            return Delivery(DeliveryPolicy.REPORT, key_fields=('oracle',))
        case WSMessageType.EXCHANGE_UNKNOWN_ASSET:
            return Delivery(DeliveryPolicy.REPORT, key_fields=('location', 'name', 'identifier'))
        case _:
            assert_never(message_type)


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

    `service` is a fixed id (an exchange's location, ROTKI_PREMIUM_SERVICE, an
    ExternalService), never a name the user chose, so two services cannot collide.
    `account` is the user's name for the rejected account, when there can be several.
    """
    key: ClassVar = UserMessageKey.AUTH
    service: str
    account: str | None


# The AuthFailure service for rotki's own premium credentials, shared so its emitters group
ROTKI_PREMIUM_SERVICE: Final = 'rotki_premium'


@dataclass(frozen=True)
class UnknownAssetSeen(MessageClassification):
    """An asset rotki does not know about.

    Prefer WSMessageType.EXCHANGE_UNKNOWN_ASSET for an exchange symbol the user can map;
    ExchangeInterface.send_unknown_asset_message already fills in the location and name.
    An exchange's internal id that no symbol stands for (bitpanda's numeric ids) cannot be
    mapped, so it stays here with the id as `identifier`.
    """
    key: ClassVar = UserMessageKey.UNKNOWN_ASSET
    identifier: str


@dataclass(frozen=True)
class LocalDbProblem(MessageClassification):
    """Our own stored data is inconsistent, or could not be written."""
    key: ClassVar = UserMessageKey.LOCAL_DB
    entry: UserMessageEntry


@dataclass(frozen=True)
class MissingPrice(MessageClassification):
    """No price could be found for an asset at a point in time.

    `asset` is null when a lookup for a batch of assets failed as a whole, and `timestamp`
    is null for a current price.
    """
    key: ClassVar = UserMessageKey.PRICE
    asset: str | None
    timestamp: int | None


@dataclass(frozen=True)
class Unsupported(MessageClassification):
    """rotki does not support this thing yet."""
    key: ClassVar = UserMessageKey.UNSUPPORTED
    feature: UserMessageFeature


@dataclass(frozen=True)
class Internal(MessageClassification):
    """An invariant broke. The user can only file a report.

    `operation` is what keeps unrelated breakages apart: with no fields, every INTERNAL
    message would share one row.
    """
    key: ClassVar = UserMessageKey.INTERNAL
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
        """
        return {
            'verbosity': verbosity,
            'value': msg,
            'key': classification.key,
            'subject': subject.serialize() if subject is not None else None,
            'fields': classification.serialize(),
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
                    policy=delivery.policy,
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

    def _store_of(self, policy: DeliveryPolicy) -> tuple[OrderedDict[str, HeldMessage], int]:
        if policy == DeliveryPolicy.STATE:
            return self._states, MAX_HELD_STATES
        if policy == DeliveryPolicy.REPORT:
            return self._reports, MAX_HELD_REPORTS
        return self._user_messages, MAX_HELD_USER_MESSAGES

    def _hold_keyed(
            self,
            envelope: dict[str, Any],
            text: str,
            key: str,
            policy: DeliveryPolicy,
            now: Timestamp,
    ) -> HeldMessage | None:
        """Keep a keyed message, replacing an earlier one with the same key.

        Must be called with the lock held. Returns the entry dropped to make room, if any.
        """
        store, limit = self._store_of(policy)
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

    def _drain(self, select: Callable[[HeldMessage], bool]) -> list[HeldMessage]:
        """Remove the held messages `select` picks and return them in the order they were
        last sent."""
        with self._lock:
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
        """
        messages = [message.serialize() for message in self._drain(lambda _: True)]
        with self._lock:
            dropped, self._dropped = self._dropped, 0
        return messages, dropped

    def clear(self) -> None:
        """Drop every held message, so none leaks into the next user's session."""
        self._drain(lambda _: True)
        with self._lock:
            self._dropped = 0

    @staticmethod
    def _is_user_warning(message: HeldMessage) -> bool:
        return (
            message.payload['type'] == WSMessageType.USER_MESSAGE and
            message.payload['data']['verbosity'] == 'warning'
        )

    def consume_warnings(self) -> list[str]:
        """Drain the held user warnings as rendered text, once per time each was sent."""
        return [
            message.text
            for message in self._drain(self._is_user_warning)
            for _ in range(message.count)
        ]

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
        """Drain every held message but the user warnings as text, once per time each was
        sent: the rendered sentence of a user error, the serialized payload of the rest."""
        return [message.text for message in self._consume_non_warnings()]

    def consume_error_payloads(self) -> list[dict[str, Any]]:
        """Like consume_errors, as the `{type, data}` objects the websocket sends."""
        return [message.payload for message in self._consume_non_warnings()]

    def _consume_non_warnings(self) -> list[HeldMessage]:
        return [
            message
            for message in self._drain(lambda message: not self._is_user_warning(message))
            for _ in range(message.count)
        ]

    @staticmethod
    def how_many_events_per_ws(total_events: int) -> int:
        """
        Scales the number of events needed to send a WS message. Start from 5 and scale up to 50
        linearly if total events >= 1000.
        """
        return min(50, max(5, 5 + max(0, total_events - 50) // 20))
