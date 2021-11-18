import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.errors import RemoteError
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.typing import Price

PRICE_API_URL = 'https://bisq.markets/api/ticker?market={symbol}_BTC'


def get_bisq_market_price(asset: Asset) -> Price:
    """
    Get price for pair at bisq marketplace. Price is returned agains BTC.
    Can raise:
    - RemoteError: If the market doesn't exists or request fails
    - DeserializationError: If the data returned is not a valid price
    """
    symbol = asset.symbol
    url = PRICE_API_URL.format(symbol=symbol)
    try:
        response = requests.get(url, timeout=DEFAULT_TIMEOUT_TUPLE)
    except requests.exceptions.RequestException as e:
        raise RemoteError(f'bisq.markets request {url} failed due to {str(e)}') from e

    data = response.json()
    if 'error' in data:
        raise RemoteError(f'Request data from bisq.markets {url} is not valid {data["error"]}')

    return deserialize_price(data['last'])
