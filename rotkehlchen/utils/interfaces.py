from abc import ABCMeta, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Optional

from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.premium.premium import Premium
    from rotkehlchen.user_messages import MessagesAggregator


class EthereumModule(metaclass=ABCMeta):
    """Interface to be followed by all Ethereum modules"""

    @abstractmethod
    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
            premium: Optional['Premium'],
            msg_aggregator: 'MessagesAggregator',
            **kwargs: Any,
    ) -> None:
        ...

    # Optional callback to run on a module's startup
    # Is optional as opposed to a no-op  since at initialization we
    # start a greenlet to run it and there is no reason to bring up no-op greenlets
    on_startup: Callable[['EthereumModule'], None] | None = None

    @abstractmethod
    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        """Actions to run on new ethereum account additions

        Can optionally return a list of asset balances determined by the module
        """

    @abstractmethod
    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        """Actions to run on removal of an ethereum account"""

    @abstractmethod
    def deactivate(self) -> None:
        """Actions to run on module's deactivation"""


class ProgressUpdater(metaclass=ABCMeta):
    """Interface to be followed to give progress updates about something to the frontend

    Is designed to be used by processes that update progress for state changes like
    DB Upgrades and Data Migrations
    """

    def __init__(self, messages_aggregator: 'MessagesAggregator', target_version: int) -> None:
        self.messages_aggregator = messages_aggregator
        self.target_version = target_version
        self.start_version: int | None = None
        self.current_version: int | None = None
        self.current_round_total_steps = 0
        self.current_round_current_step = 0

    def new_round(self, version: int) -> None:
        """
        Should be called when a new round for upgrade/migration starts but
        before `set_total_steps`. Notifies users about the new round.
        """
        if self.start_version is None:
            self.start_version = version

        self.current_version = version
        self.current_round_total_steps = 0
        self.current_round_current_step = 0
        self._notify_frontend()

    def set_total_steps(self, steps: int) -> None:
        """
        Should be called when new round starts but after `new_round` method.
        Sets total steps that the new round consists of.
        """
        self.current_round_total_steps = steps

    def new_step(self, name: str | None = None) -> None:
        """
        Should be called when currently running round reaches a new step.
        Informs users about the new step. Total number of calls to this method must be equal to
        the total number of steps set via `set_total_steps`.
        """
        self.current_round_current_step += 1
        self._notify_frontend(name)

    @abstractmethod
    def _notify_frontend(self, step_name: str | None = None) -> None:
        """Sends to the user through websockets all information about progress."""
