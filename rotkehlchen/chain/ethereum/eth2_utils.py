import logging
from bs4 import BeautifulSoup, SoupStrainer
from typing import Dict, NamedTuple

import requests

from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.typing import Timestamp
from rotkehlchen.utils.misc import create_timestamp, from_gwei

log = logging.getLogger(__name__)


class ValidatorBalance(NamedTuple):
    epoch: int
    balance: int  # in gwei
    effective_balance: int  # in wei


def _serialize_gwei_with_price(value: int, eth_usd_price: FVal) -> Dict[str, str]:
    normalized_value = from_gwei(value)
    return {
        'amount': str(normalized_value),
        'usd_value': str(normalized_value * eth_usd_price),
    }


class ValidatorPerformance(NamedTuple):
    balance: int  # in gwei
    performance_1d: int  # in gwei
    performance_1w: int  # in gwei
    performance_1m: int  # in gwei
    performance_1y: int  # in gwei

    def serialize(self, eth_usd_price: FVal) -> Dict[str, Dict[str, str]]:
        return {
            'balance': _serialize_gwei_with_price(self.balance, eth_usd_price),
            'performance_1d': _serialize_gwei_with_price(self.performance_1d, eth_usd_price),
            'performance_1w': _serialize_gwei_with_price(self.performance_1w, eth_usd_price),
            'performance_1m': _serialize_gwei_with_price(self.performance_1m, eth_usd_price),
            'performance_1y': _serialize_gwei_with_price(self.performance_1y, eth_usd_price),
        }


DEPOSITING_VALIDATOR_PERFORMANCE = ValidatorPerformance(
    balance=32000000000,
    performance_1d=0,
    performance_1w=0,
    performance_1m=0,
    performance_1y=0,
)


class ValidatorID(NamedTuple):
    # not using index due to : https://github.com/python/mypy/issues/9043
    validator_index: int
    public_key: str


class ValidatorDailyStats(NamedTuple):
    timestamp: Timestamp
    pnl: FVal
    start_balance: FVal
    end_balance: FVal
    missed_attestations: int = 0
    orphaned_attestations: int = 0
    proposed_blocks: int = 0
    missed_blocks: int = 0
    orphaned_blocks: int = 0
    included_attester_slashings: int = 0
    proposer_attester_slashings: int = 0
    deposits_number: int = 0
    amount_deposited: FVal = ZERO


def _parse_fval(line: str, entry: str) -> FVal:
    try:
        result = FVal(line.replace('ETH', ''))
    except ValueError as e:
        raise RemoteError(f'Could not parse {line} as a number') from e

    return result


def _parse_int(line: str, entry: str) -> FVal:
    try:
        if line == '-':
            result = 0
        else:
            result = int(line)
    except ValueError as e:
        raise RemoteError(f'Could not parse {line} as an integer') from e

    return result


def get_validator_daily_stats(validator_index: int, last_known_timestamp: Timestamp):
    """Scrapes the website of beaconcha.in and parses the data directly out of the data table.

    The parser is very simple. And can break if they change stuff in the way
    it's displayed in https://beaconcha.in/validator/33710/stats. If that happpens
    we need to adjust here. If we also somehow programatically get the data in a CSV
    that would be swell.

    May raise:
    - RemoteError if we can't query beaconcha.in or if the data is not in the expected format
    """
    url = f'https://beaconcha.in/validator/{validator_index}/stats'
    log.debug(f'Querying beaconchain stats: {url}')
    try:
        response = requests.get(url)
    except requests.exceptions.RequestException as e:
        raise RemoteError(f'Beaconcha.in api request {url} failed due to {str(e)}')

    if response.status_code != 200:
        raise RemoteError(
            f'Beaconcha.in api request {url} failed with code: {response.status_code}'
            f' and response: {response.text}',
        )

    soup = BeautifulSoup(response.text, 'html.parser', parse_only=SoupStrainer('tbod'))
    if soup is None:
        raise RemoteError('Could not find <tbod> while parsing beaconcha.in stats page')
    try:
        tr = soup.tbod.tr
    except AttributeError as e:
        raise RemoteError('Could not find first <tr> while parsing beaconcha.in stats page') from e

    timestamp = 0
    pnl = ZERO,
    start_balance = ZERO
    end_balance = ZERO
    missed_attestations = 0
    orphaned_attestations = 0
    proposed_blocks = 0
    missed_blocks = 0
    orphaned_blocks = 0
    included_attester_slashings = 0
    proposer_attester_slashings = 0
    deposits_number = 0
    amount_deposited = FVal
    column_pos = 1
    stats = []
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

                if timestamp <= last_known_timestamp:
                    return stats  # we are done

                column_pos += 1
            elif column_pos == 2:
                pnl = _parse_fval(column.string, 'income')
                column_pos += 1
            elif column_pos == 3:
                start_balance = _parse_fval(column.string, 'start balance')
                column_pos += 1
            elif column_pos == 4:
                end_balance = _parse_fval(column.string, 'end balance')
                column_pos += 1
            elif column_pos == 5:
                missed_attestations = _parse_int(column.string, 'missed attestations')
                column_pos += 1
            elif column_pos == 6:
                orphaned_attestations = _parse_int(column.string, 'orphaned attestations')
                column_pos += 1
            elif column_pos == 7:
                proposed_blocks = _parse_int(column.string, 'proposed blocks')
                column_pos += 1
            elif column_pos == 8:
                missed_blocks = _parse_int(column.string, 'missed blocks')
                column_pos += 1
            elif column_pos == 9:
                orphaned_blocks = _parse_int(column.string, 'orphaned blocks')
                column_pos += 1
            elif column_pos == 10:
                included_attester_slashings = _parse_int(column.string, 'included attester slashings')  # noqa: E501
                column_pos += 1
            elif column_pos == 11:
                proposer_attester_slashings = _parse_int(column.string, 'proposer attester slashings')  # noqa: E501
                column_pos += 1
            elif column_pos == 12:
                deposits_number = _parse_int(column.string, 'deposits number')
                column_pos += 1
            elif column_pos == 13:
                amount_deposited = _parse_fval(column.string, 'amount deposited')
                column_pos += 1

        column_pos = 1
        stats.append(ValidatorDailyStats(
            timestamp=timestamp,
            pnl=pnl,
            start_balance=start_balance,
            end_balance=end_balance,
            missed_attestations=missed_attestations,
            orphaned_attestations=orphaned_attestations,
            proposed_blocks=proposed_blocks,
            missed_blocks=missed_blocks,
            orphaned_blocks=orphaned_blocks,
            included_attester_slashings=included_attester_slashings,
            proposer_attester_slashings=proposer_attester_slashings,
            deposits_number=deposits_number,
            amount_deposited=amount_deposited,
        ))
        tr = tr.find_next_sibling()

    return stats
