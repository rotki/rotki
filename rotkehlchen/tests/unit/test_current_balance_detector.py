from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.detectors.current_balance import (
    CurrentBalanceMismatchDetector,
    run_current_balance_detection,
)
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.types import DataIssueFilters
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1, TEST_ADDR2
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import EventMetricKey, Location, TimestampMS

pytestmark = [
    pytest.mark.accounting_update,
    pytest.mark.parametrize('use_clean_caching_directory', [True]),
]

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import ChecksumEvmAddress

ETH_LOCATION = Location.ETHEREUM.serialize_for_db()
TOLERANCE = FVal('0.001')


def _add_balance(database: DBHandler, address: str, balance: str, ts: int = 1_000) -> int:
    """Add an event and the derived balance metric the processor would have written for it."""
    with database.user_write() as write_cursor:
        event_id = DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(ts),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal(balance),
                location_label=address,
            ),
        )
        write_cursor.execute(
            'INSERT INTO event_metrics(event_identifier, location, location_label, protocol, '
            'metric_key, metric_value, asset, timestamp, sequence_index, sort_key) '
            'VALUES (?, ?, ?, NULL, ?, ?, ?, ?, 0, ?)',
            (
                event_id, ETH_LOCATION, address, EventMetricKey.BALANCE.serialize(), balance,
                A_ETH.identifier, ts, ts,
            ),
        )
    assert event_id is not None
    return event_id


def _make_detector(
        database: DBHandler,
        observed: str | None,
) -> CurrentBalanceMismatchDetector:
    def reader(
            location: Location,
            address: ChecksumEvmAddress,
            assets: Sequence[str],
    ) -> dict[str, FVal]:
        if observed is None:
            raise RemoteError('node down')
        return {asset: FVal(observed) for asset in assets}

    return CurrentBalanceMismatchDetector(
        database=database,
        observed_balance_reader=reader,
        tolerance=TOLERANCE,
    )


def _get_issues(database: DBHandler) -> list:
    return DataIssuesManager(database).list_issues(
        DataIssueFilters(kind=IssueKind.CURRENT_BALANCE_MISMATCH),
    )


def test_divergence_outside_tolerance_writes_an_issue(database: DBHandler) -> None:
    event_id = _add_balance(database, TEST_ADDR1, '5')
    assert _make_detector(database, '3').run() == 1
    assert len(issues := _get_issues(database)) == 1
    assert issues[0].state == IssueState.OPEN
    assert issues[0].location_label == TEST_ADDR1
    assert issues[0].asset == A_ETH.identifier
    assert issues[0].ts_start == 1_000
    assert issues[0].payload['derived_balance'] == '5'
    assert issues[0].payload['observed_balance'] == '3'
    assert issues[0].payload['delta'] == '-2'
    assert issues[0].payload['latest_event_identifier'] == event_id


def test_divergence_within_tolerance_writes_nothing(database: DBHandler) -> None:
    _add_balance(database, TEST_ADDR1, '5')
    assert _make_detector(database, '5.0005').run() == 1
    assert _get_issues(database) == []


def test_repeated_detection_updates_the_issue_instead_of_duplicating(
        database: DBHandler,
) -> None:
    _add_balance(database, TEST_ADDR1, '5')
    _make_detector(database, '3').run()
    _make_detector(database, '2').run()
    assert len(issues := _get_issues(database)) == 1
    assert issues[0].payload['observed_balance'] == '2'
    assert issues[0].payload['delta'] == '-3'


def test_narrowed_divergence_resolves_the_issue(database: DBHandler) -> None:
    _add_balance(database, TEST_ADDR1, '5')
    _make_detector(database, '3').run()
    _make_detector(database, '5').run()
    assert len(issues := _get_issues(database)) == 1
    assert issues[0].state == IssueState.RESOLVED
    assert issues[0].payload['resolution'] == {'reason': 'within_tolerance'}


def test_unresolved_issue_reopens_only_when_the_divergence_grows(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    _add_balance(database, TEST_ADDR1, '5')
    _make_detector(database, '3').run()
    issue_id = _get_issues(database)[0].id
    manager.update_state(issue_id, IssueState.AUTO_REMEDIATING)
    manager.update_state(issue_id, IssueState.UNRESOLVED)

    _make_detector(database, '4').run()  # smaller than the delta of 2 it was unresolved at
    assert manager.get_issue(issue_id).state == IssueState.UNRESOLVED

    _make_detector(database, '1').run()  # larger
    assert manager.get_issue(issue_id).state == IssueState.OPEN


def test_dismissed_issue_is_left_alone(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    _add_balance(database, TEST_ADDR1, '5')
    _make_detector(database, '3').run()
    manager.dismiss(issue_id := _get_issues(database)[0].id)
    _make_detector(database, '1').run()
    _make_detector(database, '5').run()
    assert manager.get_issue(issue_id).state == IssueState.DISMISSED


def test_unreachable_chain_neither_opens_nor_resolves(database: DBHandler) -> None:
    _add_balance(database, TEST_ADDR1, '5')
    _make_detector(database, '3').run()
    assert _make_detector(database, None).run() == 0
    assert _get_issues(database)[0].state == IssueState.OPEN


def test_from_ts_restricts_checked_buckets(database: DBHandler) -> None:
    _add_balance(database, TEST_ADDR1, '5', ts=1_000)
    _add_balance(database, TEST_ADDR2, '5', ts=9_000)
    assert _make_detector(database, '3').run(from_ts=TimestampMS(5_000)) == 1
    assert [issue.location_label for issue in _get_issues(database)] == [TEST_ADDR2]


def test_time_budget_stops_the_run(database: DBHandler) -> None:
    _add_balance(database, TEST_ADDR1, '5')
    detector = _make_detector(database, '3')
    detector.time_budget = -1
    assert detector.run() == 0
    assert _get_issues(database) == []


def test_unexpected_reader_failure_skips_the_address_instead_of_crashing(
        database: DBHandler,
) -> None:
    _add_balance(database, TEST_ADDR1, '5')

    def reader(*_args: object) -> dict[str, FVal]:
        raise BlockchainQueryError('execution reverted')

    assert CurrentBalanceMismatchDetector(
        database=database,
        observed_balance_reader=reader,
        tolerance=TOLERANCE,
    ).run() == 0
    assert _get_issues(database) == []


def test_crashed_detection_still_records_its_run(database: DBHandler) -> None:
    with (
        patch(
            'rotkehlchen.history.data_issues.detectors.current_balance.'
            'CurrentBalanceMismatchDetector.run',
            side_effect=ZeroDivisionError,
        ),
        pytest.raises(ZeroDivisionError),
    ):
        run_current_balance_detection(database=database, chains_aggregator=None)  # type: ignore[arg-type]  # never reached

    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.LAST_CURRENT_BALANCE_DETECTION_TS,
        ) is not None
