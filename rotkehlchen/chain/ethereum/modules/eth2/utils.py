import logging
import re
from http import HTTPStatus
from typing import Literal, Optional

import gevent
import requests
from bs4 import BeautifulSoup, SoupStrainer

from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.beaconchain import BEACONCHAIN_ROOT_URL
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import create_timestamp

from .structures import ValidatorDailyStats

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DAY_AFTER_ETH2_GENESIS = Timestamp(1606780800)
INITIAL_ETH_DEPOSIT = FVal(32)
EPOCH_DURATION_SECS = 384

EPOCH_PARSE_REGEX = re.compile(r'<a href="/epoch/(.*?)">.*')
ADDRESS_PARSE_REGEX = re.compile(r'<a href="/address/(.*?)".*')
ETH_PARSE_REGEX = re.compile(r'.*title="(.*?)">.*')
ETH2_GENESIS_TIMESTAMP = 1606824023


def epoch_to_timestamp(epoch: int) -> Timestamp:
    return Timestamp(ETH2_GENESIS_TIMESTAMP + epoch * EPOCH_DURATION_SECS)


def _parse_fval(line: str, entry: str) -> FVal:
    try:
        result = FVal(line.replace('ETH', ''))
    except ValueError as e:
        raise RemoteError(f'Could not parse {line} as a number for {entry}') from e

    return result


def _query_page(url: str, event: Literal['stats', 'withdrawals']) -> requests.Response:
    """Query a single page and return the response

    May raise:
    - RemoteError if there is a request failure to beaconcha.in site
    """
    tries = 1
    max_tries = 3
    backoff = 60
    timeout = CachedSettings().get_timeout_tuple()
    while True:
        log.debug(f'Querying beaconcha.in {event}: {url}')
        try:
            response = requests.get(url, timeout=timeout)
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Beaconcha.in api request {url} failed due to {e!s}') from e

        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS and tries <= max_tries:
            sleep_secs = backoff * tries / max_tries
            log.warning(
                f'Querying {url} returned 429. Backoff try {tries} / {max_tries}.'
                f' We are backing off for {sleep_secs}',
            )
            tries += 1
            gevent.sleep(sleep_secs)
            continue

        if response.status_code != 200:
            raise RemoteError(
                f'Beaconcha.in api request {url} failed with code: {response.status_code}'
                f' and response: {response.text}',
            )

        break  # else all good - break from the loop

    return response


def scrape_validator_daily_stats(
        validator_index: int,
        last_known_timestamp: Timestamp,
        exit_ts: Optional[Timestamp],
) -> list[ValidatorDailyStats]:
    """Scrapes the website of beaconcha.in and parses the data directly out of the data table.

    The parser is very simple. And can break if they change stuff in the way
    it's displayed in https://beaconcha.in/validator/33710/stats. If that happpens
    we need to adjust here. If we also somehow programatically get the data in a CSV
    that would be swell.

    Update: They got the balancehistory endpoint which still lacks some pagination properties
    we need but should eventually replace this.
    https://beaconcha.in/api/v1/docs/index.html#/Validator/get_api_v1_validator__indexOrPubkey__balancehistory

    May raise:
    - RemoteError if we can't query beaconcha.in or if the data is not in the expected format
    """
    url = f'{BEACONCHAIN_ROOT_URL}/validator/{validator_index}/stats'
    response = _query_page(url, 'stats')
    log.debug(f'Got beaconcha.in stats results for {validator_index=}. Processing it.')
    soup = BeautifulSoup(response.text, 'html.parser', parse_only=SoupStrainer('tbod'))
    if soup is None:
        raise RemoteError('Could not find <tbod> while parsing beaconcha.in stats page')
    try:
        tr = soup.tbod.tr
    except AttributeError as e:
        raise RemoteError('Could not find first <tr> while parsing beaconcha.in stats page') from e

    timestamp = Timestamp(0)
    pnl = ZERO
    column_pos = 1
    stats: list[ValidatorDailyStats] = []
    while tr is not None:
        skip_row = False
        for column in tr.children:
            if column.name != 'td':
                continue

            if column_pos == 1:  # date
                date = column.string
                try:
                    timestamp = create_timestamp(date, formatstr='%d %b %Y')
                except ValueError as e:
                    raise RemoteError(f'Failed to parse {date} to timestamp') from e

                if timestamp <= last_known_timestamp or (exit_ts is not None and timestamp > exit_ts):  # noqa: E501
                    return stats  # we are done

                column_pos += 1
            elif column_pos == 2:
                pnl = _parse_fval(column.string, 'income')
                # if the validator makes profit in the genesis day beaconchain returns a
                # profit of deposit + validation reward. We need to subtract the deposit value
                # to obtain the actual pnl.
                # Example: https://beaconcha.in/validator/999/stats
                if pnl > ONE and timestamp == DAY_AFTER_ETH2_GENESIS:
                    pnl -= INITIAL_ETH_DEPOSIT

                column_pos += 1

            elif column_pos == 3:
                start = _parse_fval(column.string, 'start')
                if start == ZERO:
                    column_pos += 1  # keep checking columns for all zeros
                else:
                    break  # next row

            elif column_pos == 4:
                end = _parse_fval(column.string, 'end')
                if end == ZERO:
                    column_pos += 1  # keep checking columns for all zeros
                else:
                    break  # next row

            elif 5 <= column_pos <= 12:
                column_pos += 1  # skip columns

            elif column_pos == 13:
                amount = _parse_fval(column.string, 'deposit amount')
                if amount == ZERO:
                    skip_row = True  # This is a zero row. Validator has exited. Skip it
                else:
                    break  # next row

        column_pos = 1
        if skip_row is False:
            stats.append(ValidatorDailyStats(
                validator_index=validator_index,
                timestamp=timestamp,
                pnl=pnl,
            ))
        tr = tr.find_next_sibling()

    return stats
