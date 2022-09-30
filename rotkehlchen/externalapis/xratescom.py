import logging
from typing import Dict

import requests

from rotkehlchen.assets.asset import FiatAsset
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price, Timestamp
from rotkehlchen.utils.misc import timestamp_to_date

from .session import GlobalRequestsHTML

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _scrape_xratescom_exchange_rates(url: str) -> Dict[FiatAsset, Price]:
    """
    Scrapes x-rates.com website for the exchange rates tables

    May raise:
    - RemoteError if we can't query x-rates.com
    """
    log.debug(f'Querying x-rates.com stats: {url}')
    prices = {}
    try:
        response = GlobalRequestsHTML().session().get(url=url, timeout=DEFAULT_TIMEOUT_TUPLE)
    except requests.exceptions.RequestException as e:
        raise RemoteError(f'x-rates.com request {url} failed due to {str(e)}') from e

    if response.status_code != 200:
        raise RemoteError(
            f'x-rates.com request {url} failed with code: {response.status_code}'
            f' and response: {response.text}',
        )
    response.html.render()

    try:
        elements = response.html.find("table.tablesorter > tbody", first=True).find('tr')
    except AttributeError as e:
        raise RemoteError('Could not find <table> while parsing x-rates stats page') from e

    for row in elements:
        columns = row.find('td')
        if len(columns) != 3:
            raise RemoteError('Could not find proper row <td> while parsing x-rates stats page')

        link = columns[1].find('td > a', first=True)
        if link is None or 'href' not in link.attrs:
            raise RemoteError(f'Could not find <a href in {columns[1].html} while parsing x-rates.com page')  # noqa: E501

        parts = link.attrs['href'].split('to=')
        if len(parts) != 2:
            raise RemoteError(f'Could not find to= in {link.attrs["href"]} while parsing x-rates.com page')  # noqa: E501

        try:
            to_asset = FiatAsset(parts[1])
        except UnknownAsset:
            log.debug(f'Skipping {parts[1]} asset because its not a known fiat asset while parsing x-rates.com page')  # noqa: E501
            continue

        try:
            price = deserialize_price(columns[1].text)
        except DeserializationError as e:
            log.debug(f'Could not parse x-rates.com rate of {to_asset.identifier} due to {str(e)}. Skipping ...')  # noqa: E501
            continue

        prices[to_asset] = price

    return prices


def get_current_xratescom_exchange_rates(from_currency: FiatAsset) -> Dict[FiatAsset, Price]:  # noqa: E501
    """
    Get the current exchanges rates of currency from x-rates.com

    May raise:
    - RemoteError if we can't query x-rates.com
    """
    url = f'https://www.x-rates.com/table/?from={from_currency.symbol}&amount=1'
    return _scrape_xratescom_exchange_rates(url)


def get_historical_xratescom_exchange_rates(from_asset: FiatAsset, time: Timestamp) -> Dict[FiatAsset, Price]:  # noqa: E501
    """
    Get the historical exchanges rates of a currency from x-rates.com

    May raise RemoteError in case of unexpected data or no data found for timestamp
    """
    date = timestamp_to_date(time, formatstr='%Y-%m-%d')
    url = f'https://www.x-rates.com/historical/?from={from_asset.symbol}&amount=1&date={date}'
    return _scrape_xratescom_exchange_rates(url)
