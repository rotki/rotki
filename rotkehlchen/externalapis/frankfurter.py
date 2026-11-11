"""Frankfurter (https://frankfurter.dev) fiat exchange rates, based on the daily ECB
reference rates. Used as a fallback to x-rates.com for fiat to fiat rates."""
import json
import logging
from typing import TYPE_CHECKING, Final

import requests

from rotkehlchen.assets.asset import FiatAsset
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import RemoteError, cause_for_status, cause_for_undecodable_body
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import timestamp_to_date

if TYPE_CHECKING:
    from rotkehlchen.types import Price, Timestamp

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

FRANKFURTER_API_URL: Final = 'https://api.frankfurter.dev/v1'


def _query_frankfurter_exchange_rates(date: str, base: FiatAsset) -> dict[FiatAsset, Price]:
    """Query the exchange rates of `base` against all currencies Frankfurter supports.

    `date` is either 'latest' or a YYYY-MM-DD date. For a day without ECB rates, such as
    a weekend, Frankfurter returns the rates of the previous business day.

    May raise:
    - RemoteError if the query fails, the base currency or date is not supported or
    the response is malformed.
    """
    url = f'{FRANKFURTER_API_URL}/{date}?base={base.identifier}'
    log.debug('Querying frankfurter exchange rates', url=url)
    try:
        response = requests.get(url=url, timeout=CachedSettings().get_timeout_tuple())
    except requests.exceptions.RequestException as e:
        raise RemoteError(
            f'Frankfurter request {url} failed due to {e!s}',
            cause=FailureCause.NETWORK,
        ) from e

    if response.status_code != 200:
        raise RemoteError(
            f'Frankfurter request {url} failed with code: '
            f'{response.status_code} and response: {response.text}',
            cause=cause_for_status(response.status_code),
        )

    try:  # parse floats as strings to not lose precision on the way to FVal
        rates = json.loads(response.text, parse_float=str)['rates']
        rate_items = rates.items()
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as e:
        raise RemoteError(
            f'Frankfurter returned an unexpected response: {response.text}',
            cause=cause_for_undecodable_body(response.status_code),
        ) from e

    prices = {}
    for symbol, rate in rate_items:
        try:
            prices[FiatAsset(symbol)] = deserialize_price(rate)
        except (UnknownAsset, WrongAssetType, DeserializationError) as e:
            log.debug(
                'Skipping frankfurter rate',
                symbol=symbol,
                rate=rate,
                error=str(e),
            )

    return prices


def get_current_frankfurter_exchange_rates(from_currency: FiatAsset) -> dict[FiatAsset, Price]:
    """Get the latest exchange rates of a fiat currency from Frankfurter

    May raise:
    - RemoteError if we can't query Frankfurter
    """
    return _query_frankfurter_exchange_rates(date='latest', base=from_currency)


def get_historical_frankfurter_exchange_rates(
        from_asset: FiatAsset,
        time: Timestamp,
) -> dict[FiatAsset, Price]:
    """Get the exchange rates of a fiat currency at the UTC day of `time` from Frankfurter

    May raise:
    - RemoteError if we can't query Frankfurter or it has no data for the timestamp
    """
    return _query_frankfurter_exchange_rates(
        date=timestamp_to_date(time, formatstr='%Y-%m-%d'),
        base=from_asset,
    )
