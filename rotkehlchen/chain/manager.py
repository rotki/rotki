from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Generic, TypeVar

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.types import Timestamp

T_Address = TypeVar('T_Address')


class ChainManager(ABC, Generic[T_Address]):

    @abstractmethod
    def query_balances(
            self,
            addresses: Sequence[T_Address],
    ) -> dict[T_Address, BalanceSheet] | dict[T_Address, Balance]:
        """Queries balances for the blockchain"""


class ChainManagerWithTransactions(ChainManager[T_Address]):

    @abstractmethod
    def query_transactions(
            self,
            addresses: list[T_Address],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> None:
        """Query the blockchain for transactions and saves them in the DB.
        The transactions for the given time range must be included. If the APIs used for a
        particular blockchain require querying other transactions as well to reach the given
        range, then those should also be saved to avoid requerying them later.
        """
