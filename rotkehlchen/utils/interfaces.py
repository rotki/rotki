from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, List, Optional

from rotkehlchen.typing import ChecksumEthAddress

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures import AssetBalance


class EthereumModule(metaclass=ABCMeta):
    """Interface to be followed by all Ethereum modules"""

    @abstractmethod
    def on_startup(self) -> None:
        """Actions to run on startup"""
        ...

    @abstractmethod
    def on_account_addition(self, address: ChecksumEthAddress) -> Optional[List['AssetBalance']]:
        """Actions to run on new ethereum account additions

        Can optionally return a list of asset balances determined by the module
        """
        ...

    @abstractmethod
    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        """Actions to run on removal of an ethereum account"""
        ...

    @abstractmethod
    def deactivate(self) -> None:
        """Actions to run on module's deactivation"""
        ...
