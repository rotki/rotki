import json
import logging
import re
from http import HTTPStatus
from typing import Literal, NamedTuple, Optional

import gevent
import requests
from bs4 import BeautifulSoup, SoupStrainer

from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.beaconchain import BEACONCHAIN_ROOT_URL
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_evm_address,
    deserialize_fval,
    deserialize_int_from_str,
)
from rotkehlchen.types import ChecksumEvmAddress, Timestamp
from rotkehlchen.utils.misc import create_timestamp, ts_now

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


class ValidatorBalance(NamedTuple):
    epoch: int
    balance: int  # in gwei
    effective_balance: int  # in wei


def _parse_fval(line: str, entry: str) -> FVal:
    try:
        result = FVal(line.replace('ETH', ''))
    except ValueError as e:
        raise RemoteError(f'Could not parse {line} as a number for {entry}') from e

    return result


def _parse_int(line: str, entry: str) -> int:
    try:
        if line == '-':
            result = 0
        else:
            result = int(line)
    except ValueError as e:
        raise RemoteError(f'Could not parse {line} as an integer for {entry}') from e

    return result


def _query_page(url: str, event: Literal['stats', 'withdrawals']) -> requests.Response:
    """Query a single page and return the response

    May raise:
    - RemoteError if there is a request failure to beaconcha.in site
    """
    tries = 1
    max_tries = 3
    backoff = 60
    while True:
        log.debug(f'Querying beaconcha.in {event}: {url}')
        try:
            response = requests.get(url, timeout=DEFAULT_TIMEOUT_TUPLE)
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


def scrape_validator_withdrawals(
        validator_index: int,
        last_known_timestamp: Timestamp,
) -> list[tuple[Timestamp, ChecksumEvmAddress, FVal]]:
    """Kind of "scrapes" the website of beaconcha.in and parses withdrawals data.

    Will stop querying when a timestamp less than or equal to the last known
    timestamp is found.

    This should be replaced by the withdrawals endpoint.
    https://beaconcha.in/api/v1/docs/index.html#/Validator/get_api_v1_validator__indexOrPubkey__withdrawals

    Atm though it lacks pagination and ability to query history in the past.

    Here we are not really scraping ... just asking for the paginated result of the
    withdrawals data table directly.

    Returns list of withdrawals to add for the validator.

    May raise:
    - RemoteError if we can't query beaconcha.in or if the data is not in the expected format
    - DeserializationError if something is not in the expected format
    """
    withdrawals = []
    now = ts_now()
    start = 0
    page_length = 10
    stop_iterating = False

    while True:
        url = f'{BEACONCHAIN_ROOT_URL}/validator/{validator_index}/withdrawals?draw=1&columns%5B0%5D%5Bdata%5D=0&columns%5B0%5D%5Bname%5D=&columns%5B0%5D%5Bsearchable%5D=true&columns%5B0%5D%5Borderable%5D=true&columns%5B0%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B0%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B1%5D%5Bdata%5D=1&columns%5B1%5D%5Bname%5D=&columns%5B1%5D%5Bsearchable%5D=true&columns%5B1%5D%5Borderable%5D=true&columns%5B1%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B1%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B2%5D%5Bdata%5D=2&columns%5B2%5D%5Bname%5D=&columns%5B2%5D%5Bsearchable%5D=true&columns%5B2%5D%5Borderable%5D=true&columns%5B2%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B2%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B3%5D%5Bdata%5D=3&columns%5B3%5D%5Bname%5D=&columns%5B3%5D%5Bsearchable%5D=true&columns%5B3%5D%5Borderable%5D=true&columns%5B3%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B3%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B4%5D%5Bdata%5D=4&columns%5B4%5D%5Bname%5D=&columns%5B4%5D%5Bsearchable%5D=true&columns%5B4%5D%5Borderable%5D=true&columns%5B4%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B4%5D%5Bsearch%5D%5Bregex%5D=false&order%5B0%5D%5Bcolumn%5D=0&order%5B0%5D%5Bdir%5D=desc&start={start}&length={page_length}&search%5Bvalue%5D=&search%5Bregex%5D=false&_={now}'  # noqa: E501
        response = _query_page(url, 'withdrawals')
        try:
            result = response.json()
        except json.JSONDecodeError as e:
            raise RemoteError(f'Could not parse {response.text} from beaconchain as json') from e

        for entry in result['data']:  # data appears in descending time
            epoch_match = EPOCH_PARSE_REGEX.match(entry[0])
            if epoch_match is None:
                log.error(f'Failed to match epoch regex for {entry[0]}')
                raise RemoteError('Failed to parse withdrawals response from beaconchain. Check logs')  # noqa: E501
            groups = epoch_match.groups()
            if len(groups) != 1:
                log.error(f'Failed to match epoch regex for {entry[0]}')
                raise RemoteError('Failed to parse withdrawals response from beaconchain. Check logs')  # noqa: E501
            epoch = deserialize_int_from_str(groups[0], location='beaconchain epoch')
            timestamp = epoch_to_timestamp(epoch)
            if timestamp <= last_known_timestamp:
                stop_iterating = True
                break  # we already know about this withdrawal

            address_match = ADDRESS_PARSE_REGEX.match(entry[3])
            if address_match is None:
                log.error(f'Failed to match address regex for {entry[3]}')
                raise RemoteError('Failed to parse withdrawals response from beaconchain. Check logs')  # noqa: E501
            groups = address_match.groups()
            if len(groups) != 1:
                log.error(f'Failed to match address regex for {entry[3]}')
                raise RemoteError('Failed to parse withdrawals response from beaconchain. Check logs')  # noqa: E501
            address = deserialize_evm_address(groups[0])

            eth_match = ETH_PARSE_REGEX.match(entry[4])
            if eth_match is None:
                log.error(f'Failed to match eth regex for {entry[4]}')
                raise RemoteError('Failed to parse withdrawals response from beaconchain. Check logs')  # noqa: E501
            groups = eth_match.groups()
            if len(groups) != 1:
                log.error(f'Failed to match eth regex for {entry[4]}')
                raise RemoteError('Failed to parse withdrawals response from beaconchain. Check logs')  # noqa: E501
            eth_amount = deserialize_fval(groups[0], name='withdrawal ETH', location='beaconchain query')  # noqa: E501

            withdrawals.append((timestamp, address, eth_amount))

        if stop_iterating or len(withdrawals) >= result['recordsTotal']:
            break  # reached the end
        start += page_length

    return withdrawals


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
    log.debug('Got beaconcha.in stats results. Processing it.')
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

                break

        column_pos = 1
        stats.append(ValidatorDailyStats(
            validator_index=validator_index,
            timestamp=timestamp,
            pnl=pnl,
        ))
        tr = tr.find_next_sibling()

    log.debug('Processed beaconcha.in stats results. Returning it.')
    return stats
