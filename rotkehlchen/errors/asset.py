from typing import TYPE_CHECKING, Type, Union

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import CryptoAsset, CustomAsset, EvmToken, FiatAsset, Nft


POSSIBLE_ASSET = Union[
    Type['FiatAsset'],
    Type['CryptoAsset'],
    Type['CustomAsset'],
    Type['EvmToken'],
    Type['Nft'],
]


class UnknownAsset(Exception):
    def __init__(self, asset_name: str) -> None:
        self.asset_name = asset_name
        super().__init__(f'Unknown asset {asset_name} provided.')


class WrongAssetType(Exception):
    """
    Exception raisen when the resolved type of an Asset is not the one expected.
    For example A_BTC.resolve_to_evm_token() fails with this error because BTC is
    a CryptoAsset and not an EvmToken
    """

    def __init__(
            self,
            identifier: str,
            expected_type: POSSIBLE_ASSET,
            real_type: POSSIBLE_ASSET,
    ) -> None:
        self.identifier = identifier
        self.expected_type = expected_type
        self.real_type = real_type
        super().__init__(
            f'Expected asset with identifier {identifier} to be {expected_type.__name__} but in '
            f'fact it was {real_type.__name__}',
        )


class UnsupportedAsset(Exception):
    def __init__(self, asset_name: str) -> None:
        self.asset_name = asset_name
        super().__init__(f'Found asset {asset_name} which is not supported.')


class UnprocessableTradePair(Exception):
    def __init__(self, pair: str) -> None:
        self.pair = pair
        super().__init__(f'Unprocessable pair {pair} encountered.')
