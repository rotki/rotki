from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.concurrency import TaskCancelledError
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.detectors.current_balance import (
    DEFAULT_DETECTION_TIME_BUDGET,
    CurrentBalanceMismatchDetector,
    run_current_balance_detection,
)
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.types import DataIssueFilters
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tasks.historical_balances import HYPERCORE_BUCKET_PROTOCOL
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1, TEST_ADDR2
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import EventMetricKey, Location, SupportedBlockchain, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_now

pytestmark = [
    pytest.mark.accounting_update,
    pytest.mark.parametrize('use_clean_caching_directory', [True]),
    pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]]),
]

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

TOLERANCE = FVal('0.001')


def _add_balance(
        database: DBHandler,
        address: str,
        balance: str,
        ts: int = 1_000,
        location: Location = Location.ETHEREUM,
        protocol: str | None = None,
        asset: Asset = A_ETH,
) -> int:
    """Add an event and the derived balance metric the processor would have written for it."""
    with database.user_write() as write_cursor:
        event_id = DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(ts),
                location=location,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=asset,
                amount=FVal(balance),
                location_label=address,
            ),
        )
        write_cursor.execute(
            'INSERT INTO event_metrics(event_identifier, location, location_label, protocol, '
            'metric_key, metric_value, asset, timestamp, sequence_index, sort_key) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)',
            (
                event_id, location.serialize_for_db(), address, protocol,
                EventMetricKey.BALANCE.serialize(), balance,
                asset.identifier, ts, ts,
            ),
        )
    assert event_id is not None
    return event_id


def _cache_balance(
        database: DBHandler,
        address: str,
        balance: str,
        label: str = DEFAULT_BALANCE_LABEL,
        refreshed_at: int | None = None,
        blockchain: SupportedBlockchain = SupportedBlockchain.ETHEREUM,
        asset: Asset = A_ETH,
) -> None:
    """Cache the balance the chain was last seen to hold, as a balance refresh would."""
    sheet = BalanceSheet()
    sheet.assets[asset][label] = Balance(amount=FVal(balance))
    with database.user_write() as write_cursor:
        database.set_blockchain_balances_cache(
            write_cursor=write_cursor,
            blockchain=blockchain,
            balances={address: sheet},
        )
        refresh_ts = ts_now() if refreshed_at is None else Timestamp(refreshed_at)
        database.set_dynamic_cache(
            write_cursor=write_cursor,
            name=DBCacheDynamic.LAST_BLOCKCHAIN_BALANCES_QUERY_TS,
            value=refresh_ts,
            blockchain=blockchain.serialize(),
        )
        database.set_dynamic_cache(
            write_cursor=write_cursor,
            name=DBCacheDynamic.LAST_ADDRESS_BALANCES_QUERY_TS,
            value=refresh_ts,
            blockchain=blockchain.serialize(),
            address=address,
        )


def _make_detector(
        database: DBHandler,
        observed: str,
        blockchain: SupportedBlockchain = SupportedBlockchain.ETHEREUM,
) -> CurrentBalanceMismatchDetector:
    for address in (TEST_ADDR1, TEST_ADDR2):
        _cache_balance(database, address, observed, blockchain=blockchain)

    return CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE)


def _get_issues(database: DBHandler) -> list:
    return DataIssuesManager(database).list_issues(
        DataIssueFilters(kind=IssueKind.CURRENT_BALANCE_MISMATCH),
    )


def _set_pending(database: DBHandler, from_ts: int) -> None:
    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.PENDING_DETECTION_FROM_TS,
            value=Timestamp(from_ts),
        )


def _get_pending(database: DBHandler) -> int | None:
    with database.conn.read_ctx() as cursor:
        pending = database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.PENDING_DETECTION_FROM_TS,
        )

    return None if pending is None else int(pending)


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


def test_tolerance_is_relative_to_the_balance(database: DBHandler) -> None:
    _add_balance(database, TEST_ADDR1, '1000')
    _add_balance(database, TEST_ADDR2, '0.0005')
    _cache_balance(database, TEST_ADDR1, '1000.5')
    _cache_balance(database, TEST_ADDR2, '0')
    CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE).run()
    assert [issue.location_label for issue in _get_issues(database)] == [TEST_ADDR2]


def test_untracked_address_is_not_compared(database: DBHandler) -> None:
    _add_balance(database, make_evm_address(), '5')
    assert _make_detector(database, '3').run() == 0
    assert _get_issues(database) == []


@pytest.mark.parametrize('hyperliquid_accounts', [[TEST_ADDR1]])
def test_hypercore_bucket_is_not_compared_with_hyperevm(database: DBHandler) -> None:
    _add_balance(database, TEST_ADDR1, '5', location=Location.HYPERLIQUID)
    _add_balance(
        database=database,
        address=TEST_ADDR1,
        balance='7',
        location=Location.HYPERLIQUID,
        protocol=HYPERCORE_BUCKET_PROTOCOL,
    )
    assert _make_detector(database, '3', SupportedBlockchain.HYPERLIQUID).run() == 1
    assert len(issues := _get_issues(database)) == 1
    assert issues[0].payload['derived_balance'] == '5'


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


def test_nothing_cached_neither_opens_nor_resolves(database: DBHandler) -> None:
    _add_balance(database, TEST_ADDR1, '5')
    detector = _make_detector(database, '3')
    detector.run()
    with database.user_write() as write_cursor:
        database.delete_blockchain_balances_cache(write_cursor=write_cursor)

    assert detector.run() == 0
    assert _get_issues(database)[0].state == IssueState.OPEN


def test_event_newer_than_the_balance_refresh_is_not_compared(database: DBHandler) -> None:
    _add_balance(database, TEST_ADDR1, '5', ts=10_000_000)
    _cache_balance(database, TEST_ADDR1, '3', refreshed_at=9_999)
    assert CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE).run() == 0
    assert _get_issues(database) == []


def test_refresh_of_another_address_does_not_make_the_cache_current(database: DBHandler) -> None:
    _add_balance(database, TEST_ADDR1, '5', ts=10_000_000)
    _cache_balance(database, TEST_ADDR1, '3', refreshed_at=9_999)
    _cache_balance(database, TEST_ADDR2, '3', refreshed_at=20_000)
    assert CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE).run() == 0
    assert _get_issues(database) == []


def test_only_the_wallet_label_of_the_cache_is_compared(database: DBHandler) -> None:
    _add_balance(database, TEST_ADDR1, '5')
    _cache_balance(database, TEST_ADDR1, '3', label='aave-v3')
    assert CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE).run() == 0
    assert _get_issues(database) == []


def test_wallet_token_cached_under_its_own_protocol_is_compared(database: DBHandler) -> None:
    curve_token = Asset('eip155:1/erc20:0x0012940cf77a3cB5BADE409B96A60E22506CF7d0')
    _add_balance(database, TEST_ADDR1, '5', asset=curve_token)
    _cache_balance(database, TEST_ADDR1, '3', label='curve', asset=curve_token)
    assert CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE).run() == 1
    assert [issue.asset for issue in _get_issues(database)] == [curve_token.identifier]


def test_skipped_chain_is_not_compared(database: DBHandler) -> None:
    _add_balance(database, TEST_ADDR1, '5')
    detector = _make_detector(database, '3')
    with patch.object(
        CachedSettings,
        'get_settings',
        return_value=MagicMock(disabled_chain_queries={SupportedBlockchain.ETHEREUM: frozenset()}),
    ):
        assert detector.run() == 0

    assert _get_issues(database) == []


def test_skipped_address_is_not_compared_but_the_others_on_its_chain_are(
        database: DBHandler,
) -> None:
    _add_balance(database, TEST_ADDR1, '5')
    _add_balance(database, TEST_ADDR2, '5')
    detector = _make_detector(database, '3')
    with patch.object(
        CachedSettings,
        'get_settings',
        return_value=MagicMock(
            disabled_chain_queries={SupportedBlockchain.ETHEREUM: frozenset({TEST_ADDR1})},
        ),
    ):
        assert detector.run() == 1

    assert [issue.location_label for issue in _get_issues(database)] == [TEST_ADDR2]


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


def test_full_run_out_of_budget_resumes_where_it_stopped(database: DBHandler) -> None:
    _add_balance(database, TEST_ADDR1, '5')
    _add_balance(database, TEST_ADDR2, '5')
    detector = _make_detector(database, '5')
    compare, clock, queried = detector._compare, [0.0], []

    def timed_compare(**kwargs: Any) -> None:
        clock[0] += 10  # each wallet uses up the whole budget
        queried.append(kwargs['address'])
        compare(**kwargs)

    detector.time_budget = 5
    with (
        patch.object(detector, '_compare', side_effect=timed_compare),
        patch(
            'rotkehlchen.history.data_issues.detectors.current_balance.time.monotonic',
            side_effect=lambda: clock[0],
        ),
    ):
        for _ in range(3):
            detector.run()
        detector.run(from_ts=TimestampMS(0))  # a scoped run neither follows nor moves the cursor
        detector.run()

    first, second = sorted((TEST_ADDR1, TEST_ADDR2))
    assert queried == [first, second, first, first, second]


def test_crashed_detection_still_records_its_run_and_reports_it(database: DBHandler) -> None:
    _set_pending(database, 0)
    with (
        patch(
            'rotkehlchen.history.data_issues.detectors.current_balance.'
            'CurrentBalanceMismatchDetector.run',
            side_effect=ZeroDivisionError,
        ),
        pytest.raises(ZeroDivisionError),
    ):
        run_current_balance_detection(
            database=database,
            msg_aggregator=(msg_aggregator := MagicMock()),
        )

    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.LAST_CURRENT_BALANCE_DETECTION_TS,
        ) is not None
    assert _get_pending(database) is None
    msg_aggregator.add_message.assert_called_once_with(
        message_type=WSMessageType.CURRENT_BALANCE_DETECTION_COMPLETED,
        data={},
    )


def test_cancelled_detection_still_reports_its_end(database: DBHandler) -> None:
    """A cancelled task's write of its run timestamp can raise too, the message must still go"""
    with (
        patch(
            'rotkehlchen.history.data_issues.detectors.current_balance.'
            'CurrentBalanceMismatchDetector.run',
            side_effect=TaskCancelledError('cancelled'),
        ),
        patch.object(database, 'user_write', side_effect=TaskCancelledError('cancelled')),
        pytest.raises(TaskCancelledError),
    ):
        run_current_balance_detection(
            database=database,
            msg_aggregator=(msg_aggregator := MagicMock()),
        )

    msg_aggregator.add_message.assert_called_once_with(
        message_type=WSMessageType.CURRENT_BALANCE_DETECTION_COMPLETED,
        data={},
    )


def test_partial_detection_keeps_the_daily_full_run_due(database: DBHandler) -> None:
    with patch(
        'rotkehlchen.history.data_issues.detectors.current_balance.'
        'CurrentBalanceMismatchDetector.run',
        return_value=0,
    ):
        run_current_balance_detection(
            database=database,
            msg_aggregator=MagicMock(),
            from_ts=TimestampMS(5_000),
        )
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.LAST_CURRENT_BALANCE_DETECTION_TS,
        ) is None


def test_cancelled_detection_keeps_the_pending_marker(database: DBHandler) -> None:
    _set_pending(database, 0)
    with (
        patch(
            'rotkehlchen.history.data_issues.detectors.current_balance.'
            'CurrentBalanceMismatchDetector.run',
            side_effect=TaskCancelledError('cancelled'),
        ),
        pytest.raises(TaskCancelledError),
    ):
        run_current_balance_detection(database=database, msg_aggregator=MagicMock())

    assert _get_pending(database) == 0


@pytest.mark.parametrize(('time_budget', 'expected_pending'), [
    (-1, 0),  # out of budget: a scoped run can't resume, so a full run is requested
    (DEFAULT_DETECTION_TIME_BUDGET, None),
])
def test_scoped_detection_settles_the_pending_marker(
        database: DBHandler,
        time_budget: int,
        expected_pending: int | None,
) -> None:
    _add_balance(database, TEST_ADDR1, '5')
    _cache_balance(database, TEST_ADDR1, '3')
    _set_pending(database, 5_000)
    run_current_balance_detection(
        database=database,
        msg_aggregator=MagicMock(),
        from_ts=TimestampMS(0),
        time_budget=time_budget,
    )
    assert _get_pending(database) == expected_pending
