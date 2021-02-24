import logging
import re
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


PARSE_RE = re.compile(r'.*>(.*?)</')


def _parse_td(line: str, entry: str) -> str:
    match = PARSE_RE.match(line)
    if not match:
        raise RemoteError(f'Unexpected line for eth2 validator {entry}: {line}')
    groups = match.groups()
    if len(groups) != 1:
        raise RemoteError(f'Unexpected line for eth2 validator {entry}: {line}')

    return groups[0]


def _parse_fval(line: str, entry: str) -> FVal:
    try:
        td = _parse_td(line=line, entry=entry)
        result = FVal(td.replace('ETH', ''))
    except ValueError as e:
        raise RemoteError(f'Could not parse {td} as a number') from e

    return result


def _parse_int(line: str, entry: str) -> FVal:
    try:
        td = _parse_td(line=line, entry=entry)
        if td == '-':
            result = 0
        else:
            result = int(td)
    except ValueError as e:
        raise RemoteError(f'Could not parse {td} as an integer') from e

    return result


def get_validator_daily_stats(validator_index: int, last_known_timestamp: Timestamp):
    """Crawls the website of beaconcha.in and parses the data directly out of the data table.

    The parser is very very simple. And can break if they change stuff in the way
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

    result = response.text.split('<tbod>')
    if len(result) != 2:
        raise RemoteError('Could not split at <tbod> while parsing beaconcha.in stats page')

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
    column_pos = 0
    stats = []
    for line in result[1].split('\n'):
        if '<tr>' in line:
            column_pos = 1
            continue
        elif '</tr>' in line:
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
            column_pos = 0
            continue

        if column_pos == 1:  # date
            date = _parse_td(line, 'date')
            try:
                timestamp = create_timestamp(date, formatstr='%d %b %Y')
            except ValueError as e:
                raise RemoteError(f'Failed to parse {date} to timestamp') from e

            if timestamp < last_known_timestamp:
                break

            column_pos += 1
        elif column_pos == 2:
            pnl = _parse_fval(line, 'income')
            column_pos += 1
        elif column_pos == 3:
            start_balance = _parse_fval(line, 'start balance')
            column_pos += 1
        elif column_pos == 4:
            end_balance = _parse_fval(line, 'end balance')
            column_pos += 1
        elif column_pos == 5:
            missed_attestations = _parse_int(line, 'missed attestations')
            column_pos += 1
        elif column_pos == 6:
            orphaned_attestations = _parse_int(line, 'orphaned attestations')
            column_pos += 1
        elif column_pos == 7:
            proposed_blocks = _parse_int(line, 'proposed blocks')
            column_pos += 1
        elif column_pos == 8:
            missed_blocks = _parse_int(line, 'missed blocks')
            column_pos += 1
        elif column_pos == 9:
            orphaned_blocks = _parse_int(line, 'orphaned blocks')
            column_pos += 1
        elif column_pos == 10:
            included_attester_slashings = _parse_int(line, 'included attester slashings')
            column_pos += 1
        elif column_pos == 11:
            proposer_attester_slashings = _parse_int(line, 'proposer attester slashings')
            column_pos += 1
        elif column_pos == 12:
            deposits_number = _parse_int(line, 'deposits number')
            column_pos += 1
        elif column_pos == 13:
            amount_deposited = _parse_fval(line, 'amount deposited')
            column_pos += 1

    return stats
