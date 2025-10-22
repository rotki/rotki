from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Generic, TypeVar

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.chain.mixins.rpc_nodes import RPCManagerMixin
from rotkehlchen.types import Timestamp

T_Address = TypeVar('T_Address')
T_NodeInquirer = TypeVar('T_NodeInquirer', bound=RPCManagerMixin)


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


class ChainManagerWithNodesMixin(ABC, Generic[T_NodeInquirer]):
    """Mixin for chain managers that use a node inquirer that inherits from RPCManagerMixin."""

    def __init__(self, node_inquirer: T_NodeInquirer) -> None:
        self.node_inquirer = node_inquirer
