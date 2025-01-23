import abc
import json
import logging
from contextlib import suppress
from json import JSONDecodeError
from typing import Any, Final

from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_last_queried_ts_by_key,
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, Price, Timestamp
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.serialization import jsonloads_dict

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CurrentPriceOracleInterface(abc.ABC):
    """
    Interface for oracles able to query current price. Oracle could be rate limited
    """

    def __init__(self, oracle_name: str) -> None:
        self.name = oracle_name
        self.last_rate_limit = 0

    def __str__(self) -> str:
        return self.name

    def rate_limited_in_last(
            self,
            seconds: int | None = None,
    ) -> bool:
        """Denotes if the oracles has been rate limited in the last ``seconds``"""
        if seconds is None:
            return False

        return ts_now() - self.last_rate_limit <= seconds

    @abc.abstractmethod
    def query_current_price(
            self,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
    ) -> Price:
        """Query current price between two assets using oracle data.

        Returns:
            Current price between from_asset and to_asset using this oracle's data
        """

    def query_multiple_current_price(
            self,
            from_assets: list[AssetWithOracles],
            to_asset: AssetWithOracles,
    ) -> dict[AssetWithOracles, Price]:
        """Query current price between all from_assets to to_asset.

        Returns a dict mapping assets to prices found. Assets for which a price was not found
        are not included in the dict.
        """
        # TODO: Implement this function for all oracles and make this an abstract method.
        # For oracles that don't have this implemented yet,
        # simply call query_current_price for each from_asset.
        prices: dict[AssetWithOracles, Price] = {}
        for from_asset in from_assets:
            if (price := self.query_current_price(
                    from_asset=from_asset,
                    to_asset=to_asset,
            )) != ZERO_PRICE:
                prices[from_asset] = price

        return prices


class HistoricalPriceOracleInterface(CurrentPriceOracleInterface, abc.ABC):
    """Query prices for certain timestamps. Oracle could be rate limited"""

    @abc.abstractmethod
    def can_query_history(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
            seconds: int | None = None,
    ) -> bool:
        """Checks if it's okay to query historical price"""

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


class HistoricalPriceOracleWithCoinListInterface(HistoricalPriceOracleInterface, abc.ABC):
    """Historical Price Oracle with a cacheable list of all coins"""

    def __init__(self, oracle_name: str) -> None:
        super().__init__(oracle_name=oracle_name)

    def maybe_get_cached_coinlist(self, considered_recent_secs: int) -> dict[str, Any] | None:
        """Return the cached coinlist data if it exists in the DB cache and if it's recent"""
        now = ts_now()
        key_parts: Final = (CacheType.COINLIST, self.name)
        with GlobalDBHandler().conn.read_ctx() as cursor:
            last_ts = globaldb_get_unique_cache_last_queried_ts_by_key(cursor, key_parts)
            if abs(now - last_ts) <= considered_recent_secs:

                with suppress(JSONDecodeError):
                    return jsonloads_dict(globaldb_get_unique_cache_value(cursor, key_parts))  # type: ignore # due to the last_ts check get should return here

        return None

    def cache_coinlist(self, data: dict[str, Any]) -> None:
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=(CacheType.COINLIST, self.name),
                value=json.dumps(data),
            )

    @abc.abstractmethod
    def all_coins(self) -> dict[str, dict[str, Any]]:
        """Some historical price oracles (coingecko, cryptocompare) implement
        this to return all of their supported assets.

        May raise
        - RemoteError
        """
