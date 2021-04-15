from abc import ABCMeta, abstractmethod

from rotkehlchen.typing import ChecksumEthAddress


class EthereumModule(metaclass=ABCMeta):
    """Interface to be followed by all Ethereum modules"""

    @abstractmethod
    def on_startup(self) -> None:
        """Actions to run on startup"""
        ...

    @abstractmethod
    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        """Actions to run on new ethereum account additions"""
        ...

    @abstractmethod
    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        """Actions to run on removal of an ethereum account"""
        ...

    @abstractmethod
    def deactivate(self) -> None:
        """Actions to run on module's deactivation"""
        ...
