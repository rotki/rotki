from typing import Type


class UnknownAsset(Exception):
    def __init__(self, asset_name: str) -> None:
        self.asset_name = asset_name
        super().__init__(f'Unknown asset {asset_name} provided.')


class WrongAssetType(Exception):
    def __init__(
            self,
            identifier: str,
            expected_type: Type,  # Using Type instead of AssetType since when we
            real_type: Type,  # expect, for example, a crypto asset, multiple AssetTypes are possible  # noqa: E501
    ) -> None:
        self.identifier = identifier
        self.expected_type = expected_type
        self.real_type = real_type
        super().__init__(
            f'Expected asset with identifier to be {expected_type.__name__} but in fact '
            f'it was {real_type.__name__}',
        )


class UnsupportedAsset(Exception):
    def __init__(self, asset_name: str) -> None:
        self.asset_name = asset_name
        super().__init__(f'Found asset {asset_name} which is not supported.')


class UnprocessableTradePair(Exception):
    def __init__(self, pair: str) -> None:
        self.pair = pair
        super().__init__(f'Unprocessable pair {pair} encountered.')
