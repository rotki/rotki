import logging
from typing import TYPE_CHECKING, Optional, Tuple

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.interfaces import CurrentPriceOracleInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ManualPriceOracle:

    def can_query_history(  # pylint: disable=no-self-use
            self,
            from_asset: Asset,  # pylint: disable=unused-argument
            to_asset: Asset,  # pylint: disable=unused-argument
            timestamp: Timestamp,  # pylint: disable=unused-argument
            seconds: Optional[int] = None,  # pylint: disable=unused-argument
    ) -> bool:
        return True

    @classmethod
    def query_historical_price(
        cls,
        from_asset: Asset,
        to_asset: Asset,
        timestamp: Timestamp,
    ) -> Price:
        price_entry = GlobalDBHandler().get_historical_price(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
            max_seconds_distance=3600,
            source=HistoricalPriceOracle.MANUAL,
        )
        if price_entry is not None:
            log.debug('Got historical manual price', from_asset=from_asset, to_asset=to_asset, timestamp=timestamp)  # noqa: E501
            return price_entry.price

        raise NoPriceForGivenTimestamp(
            from_asset=from_asset,
            to_asset=to_asset,
            time=timestamp,
        )


class ManualCurrentOracle(CurrentPriceOracleInterface):

    def __init__(self) -> None:
        super().__init__(oracle_name='manual current price oracle')
        self.database: Optional['DBHandler'] = None

    def set_database(self, database: 'DBHandler') -> None:
        self.database = database

    def rate_limited_in_last(self, seconds: Optional[int] = None) -> bool:
        return False

    def query_current_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            match_main_currency: bool,
    ) -> Tuple[Price, bool]:
        """
        Searches for a manually specified current price for the `from_asset`.
        If it finds the price and it is the main currency, returns as is and along with a True
        value to indicate that main currency price was used.
        Otherwise converts it to a price in `to_asset` and returns it along with a False value to
        indicate no main currency matching happened.
        """
        manual_current_result = GlobalDBHandler().get_manual_current_price(
            asset=from_asset,
        )
        if manual_current_result is None:
            return Price(ZERO), False
        current_to_asset, current_price = manual_current_result
        if match_main_currency is True:
            assert self.database is not None, 'When trying to match main currency, database should be set'  # noqa: E501
            with self.database.conn.read_ctx() as cursor:
                main_currency = self.database.get_setting(cursor=cursor, name='main_currency')
                if current_to_asset == main_currency:
                    return current_price, True

        current_to_asset_price, _, used_main_currency = Inquirer().find_price_and_oracle(
            from_asset=current_to_asset,
            to_asset=to_asset,
            coming_from_latest_price=True,
            match_main_currency=match_main_currency,
        )

        return Price(current_price * current_to_asset_price), used_main_currency
