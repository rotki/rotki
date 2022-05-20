"""Named this file typedefs since either typing or types seems to conflicts with
built-in files due to a mypy bug

https://github.com/python/mypy/issues/10722
https://github.com/python/mypy/issues/1876#issuecomment-782458452
"""

from enum import Enum, auto


class WSMessageType(Enum):
    LEGACY = auto()
    BALANCE_SNAPSHOT_ERROR = auto()
    ETHEREUM_TRANSACTION_STATUS = auto()

    def __str__(self) -> str:
        return self.name.lower()  # pylint: disable=no-member


class TransactionStatusStep(Enum):
    ACCOUNT_CHANGE = auto()
    QUERYING_TRANSACTIONS = auto()
    QUERYING_INTERNAL_TRANSACTIONS = auto()
    QUERYING_ETHEREUM_TOKENS_TRANSACTIONS = auto()

    def __str__(self) -> str:
        return self.name.lower()  # pylint: disable=no-member
