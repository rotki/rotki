import logging
from typing import TYPE_CHECKING

from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.interfaces import CurrentPriceOracleInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price
from rotkehlchen.utils.interfaces import DBSetterMixin

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset, AssetWithOracles
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
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
    ) -> Price:
        """Searches for a manually specified current price for the `from_asset`.
        If found, converts it to a price in `to_asset` and returns it.
        Avoids recursion by skipping already processing asset pairs.
        """
        return self.query_multiple_current_prices(
            from_assets=[from_asset],
            to_asset=to_asset,
        ).get(from_asset, ZERO_PRICE)

    def query_multiple_current_prices(
            self,
            from_assets: list[AssetWithOracles],
            to_asset: AssetWithOracles,
    ) -> dict[AssetWithOracles, Price]:
        """Read manual prices in one query and reuse denomination conversions."""
        manual_prices = GlobalDBHandler.get_manual_current_prices(list(set(from_assets)))
        prices, conversion_prices = {}, {}
        for from_asset in from_assets:
            pair = from_asset, to_asset
            if pair in self.processing_pairs:
                log.warning(
                    'Recursive price query detected for from_asset=%s -> to_asset=%s. Skipping.',
                    from_asset,
                    to_asset,
                )
                continue
            if (manual_price := manual_prices.get(from_asset)) is None:
                continue

            self.processing_pairs.add(pair)
            try:
                current_to_asset, current_price = manual_price
                if current_to_asset not in conversion_prices:
                    conversion_prices[current_to_asset] = Inquirer.find_price(
                        from_asset=current_to_asset,
                        to_asset=to_asset,
                    )
                prices[from_asset] = Price(current_price * conversion_prices[current_to_asset])
            finally:
                self.processing_pairs.remove(pair)

        return prices
