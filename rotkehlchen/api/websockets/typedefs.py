"""Named this file typedefs since either typing or types seems to conflicts with
built-in files due to a mypy bug

https://github.com/python/mypy/issues/10722
https://github.com/python/mypy/issues/1876#issuecomment-782458452
"""

from enum import StrEnum, auto


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
    """What a user message was reading or querying when it failed.

    An enum rather than free text because the frontend groups on it: `balance` and
    `balances` as strings would be two rows for one problem, the same failure the key
    exists to remove. Members come from what the exchange emitters actually read; add one
    when an emitter reads something none of these name, never pass a near fit.
    """
    BALANCE = auto()
    TRADE = auto()
    ASSET_MOVEMENT = auto()
    HISTORY_EVENT = auto()
    MARKET = auto()
    WALLET = auto()


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
