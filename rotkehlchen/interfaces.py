import abc
from typing import Any, Dict, Optional, Tuple

from rotkehlchen.assets.asset import Asset, AssetWithOracles
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
    def query_current_price(
            self,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
            match_main_currency: bool,
    ) -> Tuple[Price, bool]:
        """
        Accepts a pair of assets to find price for and a flag. If `match_main_currency` is True
        and there is a manual latest price that has value in `main_currency`, then it will be
        returned without the conversion to `to_asset`.
        Returns:
        1. The price of from_asset at the current timestamp
        for the current oracle
        2. Whether returned price is in main currency
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
        """An oracle implements this to return a historical price from_asset to to_asset at time.

        If no price can be found may raise:
        - PriceQueryUnsupportedAsset
        - NoPriceForGivenTimestamp
        - RemoteError
        """
        ...

    @abc.abstractmethod
    def all_coins(self) -> Dict[str, Dict[str, Any]]:
        """Historical price oracles (coingecko, cryptocompare) implement this
        to return all of their supported assets.

        May raise
        - RemoteError
        """
