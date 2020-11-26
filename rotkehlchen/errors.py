from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset


class InputError(Exception):
    pass


class EthSyncError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class PremiumAuthenticationError(Exception):
    pass


class PremiumApiError(Exception):
    pass


class IncorrectApiKeyFormat(Exception):
    pass


class UnableToDecryptRemoteData(Exception):
    pass


class RotkehlchenPermissionError(Exception):
    """Raised at login if we need additional data from the user

    The payload contains information to be shown to the user by the frontend so
    they can decide what to do
    """
    def __init__(self, error_message: str, payload: Optional[Dict[str, Any]]) -> None:
        self.error_message = error_message
        self.message_payload = payload if payload is not None else {}


class SystemPermissionError(Exception):
    pass


class RemoteError(Exception):
    """Thrown when a remote API can't be reached or throws unexpected error"""
    pass


class SystemClockNotSyncedError(RemoteError):
    """Raised when the system clock is not synchronized via Internet and
    remote APIs return an error code regarding the current timestamp sent.
    """
    def __init__(self, current_time: str, remote_server: Optional[str] = None) -> None:
        self.current_time = current_time  # As str datetime
        self.remote_server = remote_server  # Remote server name
        msg_remote_server = f'{self.remote_server} server' if self.remote_server else 'server'
        super().__init__(
            f'Local system clock {self.current_time} is not sync with the {msg_remote_server}. '
            f"Please, try syncing your system's clock.",
        )


class PriceQueryUnsupportedAsset(Exception):
    def __init__(self, asset_name: str) -> None:
        self.asset_name = asset_name
        super().__init__(
            f'Unable to query historical price for unknown asset: "{self.asset_name}"')


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


class BlockchainQueryError(Exception):
    """Raises when there are problems querying a blockchain node.

    For example a VM Execution error in ethereum contract calls
    """
    pass


class XPUBError(Exception):
    """Error XPUB Parsing and address derivation"""
    pass


class EncodingError(Exception):
    pass
