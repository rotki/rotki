import logging
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.interfaces import CurrentPriceOracleInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price, Timestamp
from rotkehlchen.utils.interfaces import DBSetterMixin

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ManualPriceOracle:

    def can_query_history(
            self,
            from_asset: Asset,  # pylint: disable=unused-argument
            to_asset: Asset,  # pylint: disable=unused-argument
            timestamp: Timestamp,  # pylint: disable=unused-argument
            seconds: int | None = None,  # pylint: disable=unused-argument
    ) -> bool:
        return True

    @classmethod
    def query_historical_price(
            cls,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        price_entry = GlobalDBHandler.get_historical_price(
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


class ManualCurrentOracle(CurrentPriceOracleInterface, DBSetterMixin):

    def __init__(self) -> None:
        super().__init__(oracle_name='manual current price oracle')
        self.db: DBHandler | None = None
        self.processing_pairs: set[tuple[Asset, Asset]] = set()

    def _get_name(self) -> str:
        return self.name

    def rate_limited_in_last(self, seconds: int | None = None) -> bool:
        return False

    def query_current_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
    ) -> Price:
        """Searches for a manually specified current price for the `from_asset`.
        If found, converts it to a price in `to_asset` and returns it.
        Avoids recursion by skipping already processing asset pairs.
        """
        if (from_asset, to_asset) in self.processing_pairs:
            log.warning(f'Recursive price query detected for {from_asset=} -> {to_asset=}. Skipping.')  # noqa: E501
            return ZERO_PRICE

        self.processing_pairs.add((from_asset, to_asset))
        try:
            if (manual_current_result := GlobalDBHandler.get_manual_current_price(
                    asset=from_asset,
            )) is None:
                return ZERO_PRICE

            current_to_asset, current_price = manual_current_result

            # we call _find_price to avoid catching the recursion error at `find_price_and_oracle`.
            # ManualCurrentOracle does a special handling of RecursionError using
            # `coming_from_latest_price` to detect recursions on the manual prices and break
            # it to continue to the next oracle.
            current_to_asset_price, _ = Inquirer._find_price(
                from_asset=current_to_asset,
                to_asset=to_asset,
                coming_from_latest_price=True,
            )

            return Price(current_price * current_to_asset_price)
        finally:
            # Ensure we remove the pair after processing, even if an error occurs
            self.processing_pairs.remove((from_asset, to_asset))
