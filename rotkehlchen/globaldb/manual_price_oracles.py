import logging
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.interfaces import CurrentPriceOracleInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price
from rotkehlchen.utils.interfaces import DBSetterMixin

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


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
            current_to_asset_price = Inquirer.find_price(
                from_asset=current_to_asset,
                to_asset=to_asset,
            )
            return Price(current_price * current_to_asset_price)
        finally:
            # Ensure we remove the pair after processing, even if an error occurs
            self.processing_pairs.remove((from_asset, to_asset))
