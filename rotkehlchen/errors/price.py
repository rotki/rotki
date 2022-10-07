from rotkehlchen.assets.asset import Asset
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import timestamp_to_date


class NoPriceForGivenTimestamp(Exception):
    def __init__(
            self,
            from_asset: Asset,
            to_asset: Asset,
            time: Timestamp,
            rate_limited: bool = False,
    ) -> None:
        self.from_asset = from_asset
        self.to_asset = to_asset
        self.time = time
        self.rate_limited = rate_limited
        super().__init__(
            'Unable to query a historical price for "{}" to "{}" at {}'.format(
                from_asset.identifier,
                to_asset.identifier,
                timestamp_to_date(
                    ts=time,
                    formatstr='%d/%m/%Y, %H:%M:%S',
                    treat_as_local=True,
                ),
            ),
        )


class PriceQueryUnsupportedAsset(Exception):
    def __init__(self, asset_name: str) -> None:
        self.asset_name = asset_name
        super().__init__(
            f'Unable to query historical price for unknown asset: "{self.asset_name}"')
