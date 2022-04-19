import abc
from typing import Optional

from rotkehlchen.assets.asset import Asset
from rotkehlchen.types import Price, Timestamp


class PriceOracleInterface(metaclass=abc.ABCMeta):

    def __init__(self, oracle_name: str):
        self.oracle_name = oracle_name

    @abc.abstractmethod
    def rate_limited_in_last(
            self,
            seconds: Optional[int] = None,  # pylint: disable=unused-argument
    ) -> bool:
        ...

    @abc.abstractmethod
    def query_current_price(self, from_asset: Asset, to_asset: Asset) -> Price:
        ...

    @abc.abstractmethod
    def can_query_history(
            self,
            from_asset: Asset,  # pylint: disable=unused-argument
            to_asset: Asset,  # pylint: disable=unused-argument
            timestamp: Timestamp,  # pylint: disable=unused-argument
            seconds: Optional[int] = None,  # pylint: disable=unused-argument
    ) -> bool:
        """Checks if it's okay to query historical price"""
        ...


class CurrentPriceOracleInterface(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get_oracle_name(self) -> str:
        ...

    @abc.abstractmethod
    def query_current_price(self, from_asset: Asset, to_asset: Asset) -> Price:
        ...
