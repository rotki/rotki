"""Named this file typedefs since either typing or types seems to conflicts with
built-in files due to a mypy bug

https://github.com/python/mypy/issues/10722
https://github.com/python/mypy/issues/1876#issuecomment-782458452
"""

from dataclasses import dataclass
from enum import Enum, StrEnum, auto
from typing import Any, Final, assert_never


class WSMessageType(StrEnum):
    USER_MESSAGE = auto()
    BALANCE_SNAPSHOT_ERROR = auto()
    TRANSACTION_STATUS = auto()
    PREMIUM_STATUS_UPDATE = auto()
    DB_UPGRADE_STATUS = auto()
    # Used for evm/evmlike address migration after new chain integration
    EVMLIKE_ACCOUNTS_DETECTION = auto()
    # Used for when a new token is found and saved via processing evm/solana transactions
    NEW_TOKEN_DETECTED = auto()
    DATA_MIGRATION_STATUS = auto()
    MISSING_API_KEY = auto()
    HISTORY_EVENTS_STATUS = auto()
    REFRESH_BALANCES = auto()
    HISTORICAL_BALANCE_PROCESSING_COMPLETED = auto()
    DATABASE_UPLOAD_RESULT = auto()
    ACCOUNTING_RULE_CONFLICT = auto()
    CALENDAR_REMINDER = auto()
    EXCHANGE_UNKNOWN_ASSET = auto()
    PROGRESS_UPDATES = auto()
    GNOSISPAY_SESSIONKEY_EXPIRED = auto()
    MONERIUM_SESSIONKEY_EXPIRED = auto()
    SOLANA_TOKENS_MIGRATION = auto()
    DATABASE_UPLOAD_PROGRESS = auto()
    BINANCE_PAIRS_MISSING = auto()
    UNMATCHED_ASSET_MOVEMENTS = auto()
    UNMATCHED_BRIDGE_TRANSACTIONS = auto()
    NEGATIVE_BALANCE_DETECTED = auto()
    NO_AVAILABLE_INDEXERS = auto()
    INTERNAL_TX_FIXED = auto()
    # Sent when a price oracle is set aside for the penalty duration
    ORACLE_PENALIZED = auto()


class UserMessageKey(StrEnum):
    """Why a user message happened.

    USER_MESSAGE is the one websocket message type an emitter fills with free text: every
    other type carries a structured payload the frontend can group, title and collapse by,
    while an unclassified user message arrives as a rendered English sentence that could
    only be identified by matching it. Matching does not work -- of the 187 emitters only
    14 templates repeat at all -- so the family is declared here instead of guessed.

    The members are causes rather than consequences, because the cause is what decides
    whether the user has to act: rejected credentials are theirs to fix, an unreachable
    remote is not, and unreadable data from a remote is neither. It is also the axis the
    code already knows -- 140 of the 187 emitters sit inside an `except` clause that names
    it -- so a classification can be checked against the handler rather than taken on
    faith. The consequence (one record skipped, or a whole query lost) travels in the
    fields instead, where collapse policy can read it without inflating this enum.

    The key answers "why", the `subject` alongside it answers "to what", and the two
    together are what deduplication keys on. Keeping the subject out of the key is what
    stops this enum growing a member per exchange.
    """
    BAD_DATA = auto()  # a remote sent something we could not read
    NETWORK = auto()  # a remote could not be reached, or failed the request
    AUTH = auto()  # credentials missing, rejected or expired
    UNKNOWN_ASSET = auto()  # an asset rotki does not know about
    LOCAL_DB = auto()  # our own stored data is inconsistent or unwritable
    PRICE = auto()  # no price could be found
    UNSUPPORTED = auto()  # rotki does not support this thing yet
    INTERNAL = auto()  # an invariant broke; the user can only file a report


class UserMessageRecord(StrEnum):
    """What a user message was reading or querying from a remote when it failed.

    An enum rather than free text because the frontend groups on it: `balance` and
    `balances` as strings would be two rows for one problem, the same failure the key
    exists to remove. Members come from what the emitters actually read; add one when an
    emitter reads something none of these name, never pass a near fit.

    This is the vocabulary of remote data. What our own database holds is UserMessageEntry:
    an unreadable trade from an exchange and an unreadable trade from our DB are different
    problems with different fixes, so they must not share a row.
    """
    BALANCE = auto()
    TRADE = auto()
    ASSET_MOVEMENT = auto()
    HISTORY_EVENT = auto()
    MARKET = auto()
    WALLET = auto()
    TRANSACTION = auto()
    POSITION = auto()
    VALIDATOR = auto()
    NODE = auto()
    PROTOCOL_CACHE = auto()
    ASSET_UPDATE = auto()
    DATA_UPDATE = auto()
    PREMIUM_LIMITS = auto()


class UserMessageEntry(StrEnum):
    """What of our own stored data was inconsistent, unreadable or unwritable.

    The LOCAL_DB counterpart of UserMessageRecord, an enum for the same reason: it is what
    the frontend groups on, so free text here would reintroduce one row per spelling. The
    members are the kinds of row a user can actually be told something about, not table
    names, because the message has to end in advice ("fix this account", "re-add these
    credentials") and rows that share advice belong in one group.
    """
    DB_UPGRADE = auto()
    BLOCKCHAIN_ACCOUNT = auto()
    MARKET = auto()
    TOKEN_LIST = auto()
    MANUALLY_TRACKED_BALANCE = auto()
    BALANCE_SNAPSHOT = auto()
    EXCHANGE_CREDENTIALS = auto()
    MARGIN_POSITION = auto()
    TRANSACTION = auto()
    ASSET = auto()
    TAG = auto()
    HISTORY_EVENT = auto()
    ACCOUNTING_EVENT = auto()
    SETTING = auto()
    ADDRESSBOOK_ENTRY = auto()
    ASSET_UPDATE = auto()


class UserMessageOperation(StrEnum):
    """What rotki itself was doing when an invariant broke.

    Without it every INTERNAL message is one row: a background task that died and a data
    migration that failed would collapse together, though they are different reports to
    file. An enum for the same reason as UserMessageRecord.
    """
    BACKGROUND_TASK = auto()
    DATA_MIGRATION = auto()
    DECODER_INITIALIZATION = auto()
    TRANSACTION_DECODING = auto()
    MODULE_ACTIVATION = auto()
    BALANCE_QUERY = auto()


class UserMessageFeature(StrEnum):
    """The kind of thing rotki does not support yet.

    The kind, not the instance: a vault collateral type rotki has never seen is one row
    however many such vaults a user holds. The instance stays in the rendered sentence.
    """
    ASSET = auto()
    MULTI_TRADE = auto()
    VAULT_COLLATERAL_TYPE = auto()
    EXCHANGE_STRATEGY = auto()
    ASSET_UPDATE_SCHEMA = auto()


class ProgressUpdateSubType(StrEnum):
    UNDECODED_TRANSACTIONS = auto()
    PROTOCOL_CACHE_UPDATES = auto()
    CSV_IMPORT_RESULT = auto()
    HISTORICAL_PRICE_QUERY_STATUS = auto()
    MULTIPLE_PRICES_QUERY_STATUS = auto()
    STATS_PRICE_QUERY = auto()
    LIQUITY_STAKING_QUERY = auto()
    HISTORICAL_BALANCE_PROCESSING = auto()


class TransactionStatusStep(StrEnum):
    QUERYING_TRANSACTIONS_STARTED = auto()
    QUERYING_TRANSACTIONS = auto()
    QUERYING_INTERNAL_TRANSACTIONS = auto()
    QUERYING_EVM_TOKENS_TRANSACTIONS = auto()
    QUERYING_TRANSACTIONS_FINISHED = auto()
    QUERYING_TRANSACTIONS_FAILED = auto()
    DECODING_TRANSACTIONS_STARTED = auto()
    DECODING_TRANSACTIONS_FINISHED = auto()


class TransactionStatusSubType(StrEnum):
    EVM = auto()
    BITCOIN = auto()
    SOLANA = auto()


class HistoryEventsStep(StrEnum):
    QUERYING_EVENTS_STARTED = auto()
    QUERYING_EVENTS_STATUS_UPDATE = auto()
    QUERYING_EVENTS_FINISHED = auto()


class HistoryEventsQueryType(StrEnum):
    HISTORY_QUERY = auto()


class DBUploadStatusStep(StrEnum):
    COMPRESSING = auto()
    ENCRYPTING = auto()
    UPLOADING = auto()


class WebsocketSendError(Exception):
    """Raised when sending a message to a websocket subscriber fails"""


class DeliveryPolicy(Enum):
    """What happens to a message no client received, decided by what losing it costs."""
    LIVE = auto()  # progress of work in flight, meaningless once it is over: dropped
    EVENT = auto()  # something that happened once: every one is held, in order
    STATE = auto()  # how things are now: only the latest per key is held
    REPORT = auto()  # a failure that tends to repeat: held once per key, with a count


@dataclass(frozen=True)
class Delivery:
    """How an undelivered message of one type is held.

    `key_fields` are the data fields that tell two STATE or REPORT messages of one type
    apart, and none means one entry for the whole type. `whole_payload` keys on every
    field instead, so only exact repeats collapse.
    """
    policy: DeliveryPolicy
    key_fields: tuple[str, ...] = ()
    whole_payload: bool = False


LIVE: Final = Delivery(DeliveryPolicy.LIVE)
EVENT: Final = Delivery(DeliveryPolicy.EVENT)
LATEST: Final = Delivery(DeliveryPolicy.STATE)
EXACT_REPEATS: Final = Delivery(DeliveryPolicy.REPORT, whole_payload=True)
# A user message carries the identity its family declares as `group`, so every repeat of
# one problem is one held entry with a count and the newest sentence, whatever the text says
BY_GROUP: Final = Delivery(DeliveryPolicy.REPORT, key_fields=('group',))


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
            return Delivery(DeliveryPolicy.STATE, key_fields=('chain', 'reason'))
        case WSMessageType.MISSING_API_KEY:
            return Delivery(DeliveryPolicy.STATE, key_fields=('service', 'location'))
        case WSMessageType.CALENDAR_REMINDER:  # re-sent every few minutes until acknowledged
            return Delivery(DeliveryPolicy.STATE, key_fields=('identifier',))
        case WSMessageType.NEGATIVE_BALANCE_DETECTED:
            return Delivery(DeliveryPolicy.STATE, key_fields=('event_identifier',))
        case WSMessageType.USER_MESSAGE:
            return BY_GROUP
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
