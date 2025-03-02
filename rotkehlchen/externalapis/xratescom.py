import logging

import requests
from bs4 import BeautifulSoup, SoupStrainer

from rotkehlchen.assets.asset import FiatAsset
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price, Timestamp
from rotkehlchen.utils.misc import timestamp_to_date

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _scrape_xratescom_exchange_rates(url: str) -> dict[FiatAsset, Price]:
    """
    Scrapes x-rates.com website for the exchange rates tables

    May raise:
    - RemoteError if we can't query x-rates.com
    """
    log.debug(f'Querying x-rates.com stats: {url}')
    prices = {}
    try:
        response = requests.get(url=url, timeout=CachedSettings().get_timeout_tuple())
    except requests.exceptions.RequestException as e:
        raise RemoteError(f'x-rates.com request {url} failed due to {e!s}') from e

    if response.status_code != 200:
        raise RemoteError(
            f'x-rates.com request {url} failed with code: {response.status_code}'
            f' and response: {response.text}',
        )

    soup = BeautifulSoup(
        response.text,
        'html.parser',
        parse_only=SoupStrainer('table', {'class': 'tablesorter ratesTable'}),
    )
    if soup is None:
        raise RemoteError('Could not find <table> while parsing x-rates stats page')

    try:
        tr = soup.table.tbody.tr  # type: ignore  # we catch it with the AttributeError
    except AttributeError as e:
        raise RemoteError('Could not find first <tr> while parsing x-rates.com page') from e

    while tr is not None:
        secondtd = tr.select('td:nth-of-type(2)')[0]
        try:
            href = secondtd.a['href']  # type: ignore  # we catch it with the excepts below
        except (AttributeError, KeyError, TypeError) as e:
            raise RemoteError('Could not find a href of 2nd td while parsing x-rates.com page') from e  # noqa: E501

        parts = href.split('to=')  # type: ignore  # this is a string
        if len(parts) != 2:
            raise RemoteError(f'Could not find to= in {href} while parsing x-rates.com page')

        try:
            to_asset = FiatAsset(parts[1])
        except (UnknownAsset, WrongAssetType):
            log.debug(f'Skipping {parts[1]} asset because its not a known fiat asset while parsing x-rates.com page')  # noqa: E501
            tr = tr.find_next_sibling()
            continue

        try:
            price = deserialize_price(secondtd.a.text)  # type: ignore  # we catch it with the AttributeError
        except (DeserializationError, AttributeError) as e:
            log.debug(f'Could not parse x-rates.com rate of {to_asset.identifier} due to {e!s}. Skipping ...')  # noqa: E501
            tr = tr.find_next_sibling()
            continue

        prices[to_asset] = price
        tr = tr.find_next_sibling()

    return prices


def get_current_xratescom_exchange_rates(from_currency: FiatAsset) -> dict[FiatAsset, Price]:
    """
    Get the current exchanges rates of currency from x-rates.com

    May raise:
    - RemoteError if we can't query x-rates.com
    """
    url = f'https://www.x-rates.com/table/?from={from_currency.symbol}&amount=1'
    return _scrape_xratescom_exchange_rates(url)


def get_historical_xratescom_exchange_rates(from_asset: FiatAsset, time: Timestamp) -> dict[FiatAsset, Price]:  # noqa: E501
    """
    Get the historical exchanges rates of a currency from x-rates.com

    May raise RemoteError in case of unexpected data or no data found for timestamp
    """
    date = timestamp_to_date(time, formatstr='%Y-%m-%d')
    url = f'https://www.x-rates.com/historical/?from={from_asset.symbol}&amount=1&date={date}'
    return _scrape_xratescom_exchange_rates(url)
