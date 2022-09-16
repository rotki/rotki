import json

import requests

from rotkehlchen.assets.asset import CryptoAsset
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.types import Price

PRICE_API_URL = 'https://bisq.markets/api/ticker?market={symbol}_BTC'


def get_bisq_market_price(asset: CryptoAsset) -> Price:
    """
    Get price for pair at bisq marketplace. Price is returned against BTC.
    Can raise:
    - RemoteError: If the market doesn't exists or request fails
    - DeserializationError: If the data returned is not a valid price
    """
    url = PRICE_API_URL.format(symbol=asset.symbol)
    try:
        response = requests.get(url, timeout=DEFAULT_TIMEOUT_TUPLE)
    except requests.exceptions.RequestException as e:
        raise RemoteError(f'bisq.markets request {url} failed due to {str(e)}') from e
    try:
        data = response.json()
    except json.decoder.JSONDecodeError as e:
        raise RemoteError(
            f'Failed to read json response from bisq.markets. {response.text}. {str(e)}',
        ) from e

    if 'error' in data:
        raise RemoteError(f'Request data from bisq.markets {url} is not valid {data["error"]}')

    try:
        price = data['last']
    except KeyError as e:
        raise DeserializationError(
            f'Response from bisq.markets didnt contain expected key "last". {data}',
        ) from e
    return deserialize_price(price)
