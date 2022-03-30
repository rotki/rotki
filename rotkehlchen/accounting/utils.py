from typing import Optional

from rotkehlchen.assets.asset import Asset
from rotkehlchen.fval import FVal
from rotkehlchen.types import Price


def get_price_for_swap(
        amount_in: FVal,
        asset_in: Asset,
        amount_out: FVal,
        asset_out: Asset,
        fee: Optional[FVal],
        fee_asset: Optional[Asset],
) -> Price:
    pass
