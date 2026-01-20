from typing import Any

from rotkehlchen.assets.asset import AssetWithOracles, FiatAsset
from rotkehlchen.constants import ONE
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.serialization.serialize import process_result
from rotkehlchen.types import Price


class BalancesService:
    def __init__(self, rotkehlchen: Rotkehlchen) -> None:
        self.rotkehlchen = rotkehlchen

    def get_exchange_rates(self, given_currencies: list[AssetWithOracles]) -> dict[str, Any]:
        fiat_currencies: list[FiatAsset] = []
        asset_rates: dict[AssetWithOracles, Price] = {}
        for asset in given_currencies:
            if asset.is_fiat():
                fiat_currencies.append(asset.resolve_to_fiat_asset())
                continue

            usd_price = Inquirer.find_usd_price(asset)
            if usd_price == ZERO_PRICE:
                asset_rates[asset] = ZERO_PRICE
            else:
                asset_rates[asset] = Price(ONE / usd_price)

        asset_rates.update(Inquirer.get_fiat_usd_exchange_rates(fiat_currencies))  # type: ignore  # type narrowing does not work here
        return process_result(asset_rates)

    def query_all_balances(
            self,
            save_data: bool,
            ignore_errors: bool,
            ignore_cache: bool,
    ) -> dict[str, Any]:
        result = self.rotkehlchen.query_balances(
            requested_save_data=save_data,
            save_despite_errors=ignore_errors,
            ignore_cache=ignore_cache,
        )
        return {'result': result, 'message': ''}
