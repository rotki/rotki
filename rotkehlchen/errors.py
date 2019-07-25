#!/usr/bin/env python


class PoloniexError(Exception):
    def __init__(self, err):
        self.err = err

    def __str__(self):
        return self.err


class RecoverableRequestError(Exception):
    def __init__(self, exchange, err):
        self.exchange = exchange
        self.err = err

    def __str__(self):
        return 'While querying {} got error: "{}"'.format(self.exchange, self.err)


class InputError(Exception):
    pass


class EthSyncError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class IncorrectApiKeyFormat(Exception):
    pass


class UnableToDecryptRemoteData(Exception):
    pass


class RotkehlchenPermissionError(Exception):
    pass


class RemoteError(Exception):
    """Thrown when a remote API can't be reached or throws unexpected error"""
    pass


class PriceQueryUnknownFromAsset(Exception):
    def __init__(self, from_asset):
        super().__init__(
            'Unable to query historical price for Unknown Asset: "{}"'.format(from_asset),
        )


class UnprocessableTradePair(Exception):
    def __init__(self, pair: str):
        self.pair = pair
        super().__init__(f'Unprocessable pair {pair} encountered.')


class UnknownAsset(Exception):
    def __init__(self, asset_name: str):
        self.asset_name = asset_name
        super().__init__(f'Unknown asset {asset_name} provided.')


class UnsupportedAsset(Exception):
    def __init__(self, asset_name: str):
        self.asset_name = asset_name
        super().__init__(f'Found asset {asset_name} which is not supported.')


class HistoryCacheInvalid(Exception):
    pass


class DBUpgradeError(Exception):
    pass


class DeserializationError(Exception):
    """Raised when deserializing data from the outside and something unexpected is found"""
    pass
