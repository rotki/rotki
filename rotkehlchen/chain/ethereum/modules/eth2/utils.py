import logging
from collections.abc import Sequence
from http import HTTPStatus
from typing import Any, Literal

import gevent
import requests
from bs4 import BeautifulSoup, SoupStrainer

from rotkehlchen.api.v1.types import IncludeExcludeFilterData
from rotkehlchen.chain.ethereum.modules.eth2.constants import DEFAULT_VALIDATOR_CHUNK_SIZE
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.db.filtering import (
    EthStakingEventFilterQuery,
    EthWithdrawalFilterQuery,
    WithdrawalTypesFilter,
)
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.beaconchain.constants import BEACONCHAIN_ROOT_URL
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Eth2PubKey, Timestamp
from rotkehlchen.utils.misc import create_timestamp, get_chunks

from .structures import ValidatorDailyStats

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DAY_AFTER_ETH2_GENESIS = Timestamp(1606780800)
INITIAL_ETH_DEPOSIT = FVal(32)
EPOCH_DURATION_SECS = 384

ETH2_GENESIS_TIMESTAMP = 1606824023


def timestamp_to_epoch(timestamp: Timestamp) -> int:
    """Turn a unix timestamp to a beaconchain epoch"""
    return int((timestamp - ETH2_GENESIS_TIMESTAMP) / EPOCH_DURATION_SECS)


def epoch_to_timestamp(epoch: int) -> Timestamp:
    """Turn a beaconchain epoch to a unix timestamp"""
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
        exit_ts: Timestamp | None,
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


def form_withdrawal_notes(is_exit: bool, validator_index: int, amount: FVal) -> str:
    """Forms the ethereum withdrawal notes depending on is_exit and other attributes"""
    if is_exit is True:
        notes = f'Exited validator {validator_index} with {amount} ETH'
    else:
        notes = f'Withdrew {amount} ETH from validator {validator_index}'
    return notes


def calculate_query_chunks(
        indices_or_pubkeys: Sequence[int | Eth2PubKey],
        chunk_size: int = DEFAULT_VALIDATOR_CHUNK_SIZE,
) -> list[Sequence[int | Eth2PubKey]]:
    """Create chunks of queries.

    Beaconcha.in allows up to 100 validator or public keys in one query for most calls.
    Also has a URI length limit of ~8190, so seems no more than 80 public keys can be per call.

    Beacon nodes API has as similar limit
    https://ethereum.github.io/beacon-APIs/#/Beacon/getStateValidators
    If you cross it they will return 414 status error.

    They are creating a POST endpoint to get rid of this limit.
    """
    if len(indices_or_pubkeys) == 0:
        return []

    return list(get_chunks(indices_or_pubkeys, n=chunk_size))


def create_profit_filter_queries(common_arguments: dict[str, Any]) -> tuple[EthWithdrawalFilterQuery, EthWithdrawalFilterQuery, EthStakingEventFilterQuery]:  # noqa: E501
    """Create the Filter queries for withdrawal events and execution layer reward events"""
    withdrawals_filter_query = EthWithdrawalFilterQuery.make(
        **common_arguments,
        event_types=[HistoryEventType.STAKING],
        event_subtypes=[HistoryEventSubType.REMOVE_ASSET],
        entry_types=IncludeExcludeFilterData(values=[HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT]),
        withdrawal_types_filter=WithdrawalTypesFilter.ONLY_PARTIAL,
    )
    exits_filter_query = EthWithdrawalFilterQuery.make(
        **common_arguments,
        event_types=[HistoryEventType.STAKING],
        event_subtypes=[HistoryEventSubType.REMOVE_ASSET],
        entry_types=IncludeExcludeFilterData(values=[HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT]),
        withdrawal_types_filter=WithdrawalTypesFilter.ONLY_EXITS,
    )
    execution_filter_query = EthStakingEventFilterQuery.make(
        **common_arguments,
        event_types=[HistoryEventType.STAKING],
        event_subtypes=[HistoryEventSubType.BLOCK_PRODUCTION, HistoryEventSubType.MEV_REWARD],
        entry_types=IncludeExcludeFilterData(values=[HistoryBaseEntryType.ETH_BLOCK_EVENT]),
    )
    return withdrawals_filter_query, exits_filter_query, execution_filter_query
