from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset, CryptoAsset, CustomAsset, EvmToken, FiatAsset, Nft


POSSIBLE_ASSET = type[Union[
    'Asset',
    'FiatAsset',
    'CryptoAsset',
    'CustomAsset',
    'EvmToken',
    'Nft',
]]


class UnknownAsset(Exception):
    def __init__(self, identifier: str) -> None:
        self.identifier = identifier
        super().__init__(f'Unknown asset {identifier} provided.')


class WrongAssetType(Exception):
    """
    Exception raised when the resolved type of an Asset is not the one expected.
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
    def __init__(self, identifier: str) -> None:
        self.identifier = identifier
        super().__init__(f'Found asset {identifier} which is not supported.')


class UnprocessableTradePair(Exception):
    def __init__(self, pair: str) -> None:
        self.pair = pair
        super().__init__(f'Unprocessable pair {pair} encountered.')


class UnknownCounterpartyMapping(Exception):
    def __init__(self, symbol: str, counterparty: str) -> None:
        super().__init__(f'Cannot find {symbol} for counterparty {counterparty}')
