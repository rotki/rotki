from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Callable, List, Optional

from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.balance import AssetBalance


class EthereumModule(metaclass=ABCMeta):
    """Interface to be followed by all Ethereum modules"""

    # Optional callback to run on a module's startup
    # Is optional as opposed to a no-op  since at initialization we
    # start a greenlet to run it and there is no reason to bring up no-op greenlets
    on_startup: Optional[Callable[['EthereumModule'], None]] = None

    @abstractmethod
    def on_account_addition(self, address: ChecksumEvmAddress) -> Optional[List['AssetBalance']]:
        """Actions to run on new ethereum account additions

        Can optionally return a list of asset balances determined by the module
        """
        ...

    @abstractmethod
    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        """Actions to run on removal of an ethereum account"""
        ...

    @abstractmethod
    def deactivate(self) -> None:
        """Actions to run on module's deactivation"""
        ...
