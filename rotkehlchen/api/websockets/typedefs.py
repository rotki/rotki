"""Named this file typedefs since either typing or types seems to conflicts with
built-in files due to a mypy bug

https://github.com/python/mypy/issues/10722
https://github.com/python/mypy/issues/1876#issuecomment-782458452
"""

from enum import Enum, auto


class WSMessageType(Enum):
    LEGACY = auto()
    BALANCE_SNAPSHOT_ERROR = auto()
    EVM_TRANSACTION_STATUS = auto()
    PREMIUM_STATUS_UPDATE = auto()
    DB_UPGRADE_STATUS = auto()
    # Used for evm address migration after new chain integration
    EVM_ACCOUNTS_DETECTION = auto()
    # Used for when a new token is found and saved via processing evm transactions
    NEW_EVM_TOKEN_DETECTED = auto()
    DATA_MIGRATION_STATUS = auto()
    MISSING_API_KEY = auto()
    HISTORY_EVENTS_STATUS = auto()

    def __str__(self) -> str:
        return self.name.lower()  # pylint: disable=no-member


class TransactionStatusStep(Enum):
    QUERYING_TRANSACTIONS_STARTED = auto()
    QUERYING_TRANSACTIONS = auto()
    QUERYING_INTERNAL_TRANSACTIONS = auto()
    QUERYING_EVM_TOKENS_TRANSACTIONS = auto()
    QUERYING_TRANSACTIONS_FINISHED = auto()

    def __str__(self) -> str:
        return self.name.lower()  # pylint: disable=no-member


class HistoryEventsStep(Enum):
    QUERYING_EVENTS_STARTED = auto()
    QUERYING_EVENTS_STATUS_UPDATE = auto()
    QUERYING_EVENTS_FINISHED = auto()

    def __str__(self) -> str:
        return self.name.lower()  # pylint: disable=no-member


class HistoryEventsQueryType(Enum):
    HISTORY_QUERY = auto()

    def __str__(self) -> str:
        return self.name.lower()  # pylint: disable=no-member
