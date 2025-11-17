"""Named this file typedefs since either typing or types seems to conflicts with
built-in files due to a mypy bug

https://github.com/python/mypy/issues/10722
https://github.com/python/mypy/issues/1876#issuecomment-782458452
"""

from enum import StrEnum, auto


class WSMessageType(StrEnum):
    LEGACY = auto()
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
    SOLANA_TOKENS_MIGRATION = auto()
    DATABASE_UPLOAD_PROGRESS = auto()
    BINANCE_PAIRS_MISSING = auto()


class ProgressUpdateSubType(StrEnum):
    UNDECODED_TRANSACTIONS = auto()
    PROTOCOL_CACHE_UPDATES = auto()
    CSV_IMPORT_RESULT = auto()
    HISTORICAL_PRICE_QUERY_STATUS = auto()
    MULTIPLE_PRICES_QUERY_STATUS = auto()
    STATS_PRICE_QUERY = auto()
    LIQUITY_STAKING_QUERY = auto()


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
