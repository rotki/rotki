from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset


class RecoverableRequestError(Exception):
    def __init__(self, exchange: str, err: str) -> None:
        self.exchange = exchange
        self.err = err

    def __str__(self) -> str:
        return 'While querying {} got error: "{}"'.format(self.exchange, self.err)


class InputError(Exception):
    pass


class EthSyncError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class PremiumAuthenticationError(Exception):
    pass


class IncorrectApiKeyFormat(Exception):
    pass


class UnableToDecryptRemoteData(Exception):
    pass


class RotkehlchenPermissionError(Exception):
    pass


class SystemPermissionError(Exception):
    pass


class RemoteError(Exception):
    """Thrown when a remote API can't be reached or throws unexpected error"""
    pass


class PriceQueryUnknownFromAsset(Exception):
    def __init__(self, from_asset: 'Asset') -> None:
        super().__init__(
            f'Unable to query historical price for unknown asset: "{from_asset.identifier}"')


class UnprocessableTradePair(Exception):
    def __init__(self, pair: str) -> None:
        self.pair = pair
        super().__init__(f'Unprocessable pair {pair} encountered.')


class UnknownAsset(Exception):
    def __init__(self, asset_name: str) -> None:
        self.asset_name = asset_name
        super().__init__(f'Unknown asset {asset_name} provided.')


class UnsupportedAsset(Exception):
    def __init__(self, asset_name: str) -> None:
        self.asset_name = asset_name
        super().__init__(f'Found asset {asset_name} which is not supported.')


class DBUpgradeError(Exception):
    pass


class DeserializationError(Exception):
    """Raised when deserializing data from the outside and something unexpected is found"""
    pass


class NoPriceForGivenTimestamp(Exception):
    def __init__(self, from_asset: 'Asset', to_asset: 'Asset', date: str) -> None:
        super(NoPriceForGivenTimestamp, self).__init__(
            'Unable to query a historical price for "{}" to "{}" at {}'.format(
                from_asset.identifier, to_asset.identifier, date,
            ),
        )


class ConversionError(Exception):
    pass


class TagConstraintError(Exception):
    pass
