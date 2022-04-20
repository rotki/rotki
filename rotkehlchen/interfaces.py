import abc
from typing import Optional

from rotkehlchen.assets.asset import Asset
from rotkehlchen.types import Price, Timestamp


class CurrentPriceOracleInterface(metaclass=abc.ABCMeta):
    """
    Interface for oracles able to query current price. Oracle could be rate limited
    """

    def __init__(self, oracle_name: str) -> None:
        self.name = oracle_name

    @abc.abstractmethod
    def rate_limited_in_last(
            self,
            seconds: Optional[int] = None,
    ) -> bool:
        ...

    @abc.abstractmethod
    def query_current_price(self, from_asset: Asset, to_asset: Asset) -> Price:
        """Returns the price from_asset to to_asset at the current timestamp
        for the current oracle
        """
        ...


class HistoricalPriceOracleInterface(CurrentPriceOracleInterface):
    """Query prices for certain timestamps. Oracle could be rate limited"""

    @abc.abstractmethod
    def can_query_history(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
            seconds: Optional[int] = None,
    ) -> bool:
        """Checks if it's okay to query historical price"""
        ...

    @abc.abstractmethod
    def query_historical_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        ...
