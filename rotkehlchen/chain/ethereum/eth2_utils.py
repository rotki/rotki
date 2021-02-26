import logging
from typing import TYPE_CHECKING, List, NamedTuple, Optional

import requests
from bs4 import BeautifulSoup, SoupStrainer

from rotkehlchen.chain.ethereum.typing import ValidatorDailyStats
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.errors import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_zero_if_error
from rotkehlchen.typing import Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import create_timestamp, ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

log = logging.getLogger(__name__)


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


def _scrape_validator_daily_stats(
        validator_index: int,
        last_known_timestamp: Timestamp,
        msg_aggregator: MessagesAggregator,
) -> List[ValidatorDailyStats]:
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
        raise RemoteError(f'Beaconcha.in api request {url} failed due to {str(e)}') from e

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

    timestamp = Timestamp(0)
    pnl = ZERO
    start_amount = ZERO
    end_amount = ZERO
    missed_attestations = 0
    orphaned_attestations = 0
    proposed_blocks = 0
    missed_blocks = 0
    orphaned_blocks = 0
    included_attester_slashings = 0
    proposer_attester_slashings = 0
    deposits_number = 0
    amount_deposited = ZERO
    column_pos = 1
    stats: List[ValidatorDailyStats] = []
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
                start_amount = _parse_fval(column.string, 'start amount')
                column_pos += 1
            elif column_pos == 4:
                end_amount = _parse_fval(column.string, 'end amount')
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
        prices = [
            query_usd_price_zero_if_error(
                A_ETH,
                time=time,
                location='eth2 staking daily stats',
                msg_aggregator=msg_aggregator,
            )
            for time in (timestamp, Timestamp(timestamp + DAY_IN_SECONDS))
        ]
        stats.append(ValidatorDailyStats(
            timestamp=timestamp,
            start_usd_price=prices[0],
            end_usd_price=prices[1],
            pnl=pnl,
            start_amount=start_amount,
            end_amount=end_amount,
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


def get_validator_daily_stats(
        db: 'DBHandler',
        validator_index: int,
        msg_aggregator: MessagesAggregator,
        from_timestamp: Optional[Timestamp] = None,
        to_timestamp: Optional[Timestamp] = None,
) -> List[ValidatorDailyStats]:
    """Gets the daily stats of an ETH2 validator by index

    First queries the DB for the already known stats and then if needed also scrapes
    the beacocha.in website for more. Saves all new entries to the DB.
    """
    dbeth2 = DBEth2(db)
    known_stats = dbeth2.get_validator_daily_stats(
        validator_index=validator_index,
        from_ts=from_timestamp,
        to_ts=to_timestamp,
    )
    last_ts = Timestamp(0) if len(known_stats) == 0 else known_stats[-1].timestamp
    limit_ts = to_timestamp if to_timestamp else ts_now()
    if limit_ts - last_ts <= DAY_IN_SECONDS:
        return known_stats  # no need to requery if less than a day passed

    new_stats = _scrape_validator_daily_stats(
        validator_index=validator_index,
        last_known_timestamp=last_ts,
        msg_aggregator=msg_aggregator,
    )

    if len(new_stats) != 0:
        dbeth2.add_validator_daily_stats(validator_index=validator_index, stats=new_stats)

    return dbeth2.get_validator_daily_stats(
        validator_index=validator_index,
        from_ts=from_timestamp,
        to_ts=to_timestamp,
    )
