from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings, ModifiableDBSettings
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.bucket_checks import (
    BALANCE_CHECK_MAX_AGE,
    BucketBalanceCheck,
    BucketReason,
    BucketStatus,
    DerivedSnapshot,
    classify_bucket,
    get_balance_checks,
    save_balance_check,
)
from rotkehlchen.history.data_issues.bucket_state import (
    BucketStop,
    get_bucket_stops,
    make_bucket_key,
)
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.detectors import current_balance
from rotkehlchen.history.data_issues.detectors.current_balance import (
    CurrentBalanceMismatchDetector,
)
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.types import DataIssueFilters
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tasks import historical_balances
from rotkehlchen.tasks.historical_balances import process_historical_balances
from rotkehlchen.tests.unit.test_current_balance_detector import (
    TOLERANCE,
    _add_balance,
    _cache_balance,
    _get_issues,
    _make_detector,
)
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1, TEST_ADDR2
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import Location, SupportedBlockchain, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_now

pytestmark = pytest.mark.accounting_update
with_accounts = pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.db.dbhandler import DBHandler

ETH_LOCATION = Location.ETHEREUM.serialize_for_db()
NOW = Timestamp(2_000_000_000)


def _add_event(
        database: DBHandler,
        address: str,
        amount: str,
        timestamp: int,
        event_type: HistoryEventType = HistoryEventType.RECEIVE,
) -> int:
    with database.user_write() as write_cursor:
        event_id = DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(timestamp),
                location=Location.ETHEREUM,
                event_type=event_type,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal(amount),
                location_label=address,
            ),
        )
    assert event_id is not None
    return event_id


def _process(database: DBHandler, from_ts: int | None = None) -> None:
    process_historical_balances(
        database=database,
        msg_aggregator=database.msg_aggregator,
        from_ts=None if from_ts is None else TimestampMS(from_ts),
    )


def _stops(database: DBHandler) -> dict:
    with database.conn.read_ctx() as cursor:
        return get_bucket_stops(cursor)


def _checks(database: DBHandler) -> dict:
    with database.conn.read_ctx() as cursor:
        return get_balance_checks(cursor)


def _metric_count(database: DBHandler, address: str) -> int:
    with database.conn.read_ctx() as cursor:
        return cursor.execute(
            'SELECT COUNT(*) FROM event_metrics WHERE location_label=?', (address,),
        ).fetchone()[0]


def _bucket_key(address: str = TEST_ADDR1) -> tuple[str, str, str, str]:
    return make_bucket_key(
        location=ETH_LOCATION,
        location_label=address,
        protocol=None,
        asset=A_ETH.identifier,
    )


def _stop(database: DBHandler, address: str = TEST_ADDR1, event_id: int = 1) -> None:
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT INTO bucket_processing_stops VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (*_bucket_key(address), event_id, 1000, '5', '-1'),
        )


def _check(
        address: str = TEST_ADDR1,
        observed_at: int = NOW,
        observed_balance: int = 5,
        asset: str = 'ETH',
        compared_at: int = NOW,
) -> BucketBalanceCheck:
    return BucketBalanceCheck(
        location=ETH_LOCATION,
        location_label=address,
        asset=asset,
        derived_balance=FVal(5),
        observed_balance=FVal(observed_balance),
        latest_event_identifier=1,
        observed_at=Timestamp(observed_at),
        compared_at=Timestamp(compared_at),
    )


def _first_event_negative(database: DBHandler) -> int:
    """The first event of the bucket spends, so the bucket goes negative with no metric."""
    event_id = _add_event(database, TEST_ADDR1, '1', 1000, HistoryEventType.SPEND)
    _process(database)
    return event_id


# --- processing stops: the source of truth for blockage -----------------------------------


@with_accounts
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_first_event_negative_is_stopped_without_metrics(database: DBHandler) -> None:
    event_id = _first_event_negative(database)
    assert _metric_count(database, TEST_ADDR1) == 0
    assert _stops(database) == {_bucket_key(): BucketStop(
        event_identifier=event_id,
        event_timestamp=TimestampMS(1000),
        derived_balance_before_event=FVal(0),
        negative_amount=FVal(-1),
    )}


@with_accounts
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_dismissal_and_later_events_do_not_clear_the_stop(database: DBHandler) -> None:
    _first_event_negative(database)
    issue = DataIssuesManager(database).list_issues(DataIssueFilters(
        kind=IssueKind.NEGATIVE_BALANCE,
    ))[0]
    DataIssuesManager(database).dismiss(issue.id)
    _add_event(database, TEST_ADDR1, '10', 2000)
    _process(database)
    assert _bucket_key() in _stops(database)
    assert _metric_count(database, TEST_ADDR1) == 0  # still frozen, never a synthetic zero


@pytest.mark.parametrize('from_ts', [None, 500])
@with_accounts
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_successful_reprocessing_clears_stop_even_when_issue_is_dismissed(
        database: DBHandler,
        from_ts: int | None,
) -> None:
    _first_event_negative(database)
    issue = DataIssuesManager(database).list_issues(DataIssueFilters(
        kind=IssueKind.NEGATIVE_BALANCE,
    ))[0]
    DataIssuesManager(database).dismiss(issue.id)
    _add_event(database, TEST_ADDR1, '5', 500)  # the missing history
    _process(database, from_ts=from_ts)
    assert _stops(database) == {}
    assert _metric_count(database, TEST_ADDR1) == 2  # the repair and the formerly breaking spend
    assert DataIssuesManager(database).get_issue(issue.id).state == IssueState.DISMISSED


@with_accounts
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_failed_reprocessing_keeps_the_stop(database: DBHandler) -> None:
    _first_event_negative(database)
    _add_event(database, TEST_ADDR1, '5', 500)
    with (
        patch.object(historical_balances, '_finalize_processing', side_effect=RuntimeError),
        pytest.raises(RuntimeError),
    ):
        _process(database)
    assert _bucket_key() in _stops(database)


@with_accounts
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_partial_pass_after_the_stop_leaves_it_and_stays_frozen(database: DBHandler) -> None:
    _first_event_negative(database)
    _add_event(database, TEST_ADDR1, '10', 3000)
    _process(database, from_ts=3000)
    assert _bucket_key() in _stops(database)
    assert _metric_count(database, TEST_ADDR1) == 0


@with_accounts
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_stop_is_found_for_a_bucket_with_metrics(database: DBHandler) -> None:
    _add_event(database, TEST_ADDR1, '5', 1000)
    event_id = _add_event(database, TEST_ADDR1, '8', 2000, HistoryEventType.SPEND)
    _process(database)
    assert _metric_count(database, TEST_ADDR1) == 1
    assert _stops(database)[_bucket_key()].event_identifier == event_id
    assert _stops(database)[_bucket_key()].derived_balance_before_event == FVal(5)


# --- detector: blocked buckets, timestamps, atomicity, revalidation -----------------------


@pytest.mark.parametrize('observed', ['5', '3'])
@with_accounts
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_blocked_bucket_is_not_compared(database: DBHandler, observed: str) -> None:
    _add_balance(database, TEST_ADDR1, '5')
    _add_balance(database, TEST_ADDR2, '5')
    _stop(database)
    detector = _make_detector(database, observed)
    assert detector.run() == 1  # only the other bucket
    assert [key[1] for key in _checks(database)] == [TEST_ADDR2]
    assert [issue.location_label for issue in _get_issues(database)] == (
        [] if observed == '5' else [TEST_ADDR2]
    )


@with_accounts
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_blocked_bucket_leaves_an_existing_mismatch_issue_and_resumes_after_repair(
        database: DBHandler,
) -> None:
    _add_balance(database, TEST_ADDR1, '5')
    _make_detector(database, '3').run()  # opens the issue
    (issue,) = _get_issues(database)
    _stop(database)
    with database.user_write() as write_cursor:
        write_cursor.execute('DELETE FROM bucket_balance_checks')
    _make_detector(database, '5').run()  # matches the frozen balance
    assert _get_issues(database)[0].state == issue.state
    assert _checks(database) == {}
    with database.user_write() as write_cursor:  # successful reprocessing
        write_cursor.execute('DELETE FROM bucket_processing_stops')
    assert _make_detector(database, '5').run() == 1
    assert len(_checks(database)) == 1
    assert _get_issues(database)[0].state == IssueState.RESOLVED


@with_accounts
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_observed_at_is_preserved_when_comparing_against_an_old_cache(
        database: DBHandler,
) -> None:
    _add_balance(database, TEST_ADDR1, '5')
    observed_at = ts_now() - 1000
    for address in (TEST_ADDR1, TEST_ADDR2):
        _cache_balance(database, address, '5', refreshed_at=observed_at)
    detector = CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE)
    with patch.object(current_balance, 'ts_now', return_value=Timestamp(observed_at + 10)):
        detector.run()
    first = _checks(database)[ETH_LOCATION, TEST_ADDR1, 'ETH']
    with patch.object(current_balance, 'ts_now', return_value=Timestamp(observed_at + 500)):
        CurrentBalanceMismatchDetector(database=database, tolerance=TOLERANCE).run()
    second = _checks(database)[ETH_LOCATION, TEST_ADDR1, 'ETH']
    assert first.observed_at == second.observed_at == observed_at
    assert (first.compared_at, second.compared_at) == (observed_at + 10, observed_at + 500)


def _save(database: DBHandler, check: BucketBalanceCheck) -> None:
    with database.user_write() as write_cursor:
        save_balance_check(write_cursor, check)


@with_accounts
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_skipped_run_keeps_both_timestamps(database: DBHandler) -> None:
    _add_balance(database, TEST_ADDR1, '5', ts=10_000_000_000_000)  # newer than any observation
    _save(database, _check(observed_at=100, compared_at=200))
    assert _make_detector(database, '5').run() == 0
    saved = _checks(database)[ETH_LOCATION, TEST_ADDR1, 'ETH']
    assert (saved.observed_at, saved.compared_at) == (100, 200)


@pytest.mark.parametrize('observed', ['3', '5'])
@with_accounts
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_failure_after_the_comparison_write_rolls_back_the_issue_write(
        database: DBHandler,
        observed: str,
) -> None:
    _add_balance(database, TEST_ADDR1, '5')
    name = 'report_current_balance_mismatch' if observed == '3' else 'resolve_current_balance_mismatch'  # noqa: E501
    with (
        patch.object(DataIssuesManager, name, side_effect=RuntimeError),
        pytest.raises(RuntimeError),
    ):
        _make_detector(database, observed).run()
    assert _checks(database) == {}
    assert _get_issues(database) == []


@with_accounts
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_failure_after_the_issue_write_rolls_back_the_comparison_write(
        database: DBHandler,
) -> None:
    _add_balance(database, TEST_ADDR1, '5')
    real = CurrentBalanceMismatchDetector._update_issue

    def update_then_fail(self: CurrentBalanceMismatchDetector, **kwargs: Any) -> None:
        real(self, **kwargs)
        assert len(_get_issues(self.database)) == 1  # visible inside the transaction
        raise RuntimeError

    with (
        patch.object(CurrentBalanceMismatchDetector, '_update_issue', update_then_fail),
        pytest.raises(RuntimeError),
    ):
        _make_detector(database, '3').run()
    assert _checks(database) == {}
    assert _get_issues(database) == []


@with_accounts
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_comparison_and_issue_commit_together_and_dismissal_is_kept(database: DBHandler) -> None:
    _add_balance(database, TEST_ADDR1, '5')
    _make_detector(database, '3').run()
    assert len(_checks(database)) == 1
    (issue,) = _get_issues(database)
    DataIssuesManager(database).dismiss(issue.id)
    _make_detector(database, '2').run()
    assert _get_issues(database)[0].state == IssueState.DISMISSED
    assert _checks(database)[ETH_LOCATION, TEST_ADDR1, 'ETH'].observed_balance == FVal(2)


def _remove_account(database: DBHandler) -> None:
    with database.user_write() as write_cursor:
        database.remove_single_blockchain_accounts(
            write_cursor=write_cursor,
            blockchain=SupportedBlockchain.ETHEREUM,
            accounts=[TEST_ADDR1],
        )


def _add_stop(database: DBHandler) -> None:
    _stop(database)


def _flip_eth2_setting(database: DBHandler) -> None:
    with database.user_write() as write_cursor:
        database.set_settings(write_cursor, ModifiableDBSettings(
            treat_eth2_as_eth=CachedSettings().get_entry('treat_eth2_as_eth') is not True,
        ))


def _mark_stale(database: DBHandler) -> None:
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT INTO key_value_cache(name, value) VALUES (?, ?)',
            (DBCacheStatic.STALE_BALANCES_FROM_TS.value, '0'),
        )


@pytest.mark.parametrize('mutation', [
    _remove_account, _add_stop, _flip_eth2_setting, _mark_stale,
])
@with_accounts
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_in_flight_comparison_cannot_write_after_a_lifecycle_change(
        database: DBHandler,
        mutation: Callable[[DBHandler], None],
) -> None:
    """The change lands after the detector read its inputs and before it opens the write."""
    _add_balance(database, TEST_ADDR1, '5')
    detector = _make_detector(database, '3')
    real = current_balance.read_cached_wallet_balances

    def read_then_change(**kwargs: Any) -> dict:
        result = real(**kwargs)
        if kwargs['address'] == TEST_ADDR1:
            mutation(database)
        return result

    with patch.object(current_balance, 'read_cached_wallet_balances', read_then_change):
        assert detector.run() == 0
    assert _checks(database) == {}
    assert _get_issues(database) == []


@with_accounts
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_in_flight_comparison_cannot_write_after_a_new_observation(database: DBHandler) -> None:
    _add_balance(database, TEST_ADDR1, '5')
    detector = _make_detector(database, '3')
    real = current_balance.read_cached_wallet_balances

    def read_then_refresh(**kwargs: Any) -> dict:
        result = real(**kwargs)
        _cache_balance(database, TEST_ADDR1, '5', refreshed_at=ts_now() + 100)
        return result

    with patch.object(current_balance, 'read_cached_wallet_balances', read_then_refresh):
        assert detector.run() == 0
    assert _get_issues(database) == []


# --- lifecycle of the saved comparisons ---------------------------------------------------


@with_accounts
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_account_removal_deletes_only_its_checks(database: DBHandler) -> None:
    for address in (TEST_ADDR1, TEST_ADDR2):
        _save(database, _check(address))
    _remove_account(database)
    assert list(_checks(database)) == [(ETH_LOCATION, TEST_ADDR2, 'ETH')]


@with_accounts
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_history_reset_deletes_checks_of_cleared_accounts_only(database: DBHandler) -> None:
    _add_event(database, TEST_ADDR1, '5', 1000)
    keep = _add_event(database, TEST_ADDR1, '5', 2000)
    _add_event(database, TEST_ADDR2, '5', 1000)
    for address in (TEST_ADDR1, TEST_ADDR2):
        _save(database, _check(address))
    events_db = DBHistoryEvents(database)
    with database.user_write() as write_cursor:
        events_db.delete_events_and_track(write_cursor, 'WHERE identifier=?', (keep,))
    assert len(_checks(database)) == 2  # an event edit leaves the check to the staleness rules
    with database.user_write() as write_cursor:
        events_db.delete_events_and_track(
            write_cursor, 'WHERE location_label=?', (TEST_ADDR2,),
        )
    assert list(_checks(database)) == [(ETH_LOCATION, TEST_ADDR1, 'ETH')]


@with_accounts
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_eth2_normalization_change_deletes_eth_checks_only(database: DBHandler) -> None:
    _save(database, _check())
    _save(database, _check(asset='eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F'))
    _flip_eth2_setting(database)
    assert [key[2] for key in _checks(database)] == [
        'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F',
    ]


@with_accounts
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_checks_survive_a_setting_write_that_does_not_change_the_mapping(
        database: DBHandler,
) -> None:
    _save(database, _check())
    with database.user_write() as write_cursor:
        database.set_settings(write_cursor, ModifiableDBSettings(
            treat_eth2_as_eth=CachedSettings().get_entry('treat_eth2_as_eth') is True,
        ))
    assert len(_checks(database)) == 1


# --- the ordered classifier ---------------------------------------------------------------


DEFAULT_CHECK = BucketBalanceCheck(
    location=ETH_LOCATION,
    location_label=TEST_ADDR1,
    asset='ETH',
    derived_balance=FVal(5),
    observed_balance=FVal(5),
    latest_event_identifier=1,
    observed_at=NOW,
    compared_at=NOW,
)
DEFAULT_DERIVED = DerivedSnapshot(balance=FVal(5), latest_event_identifier=1)


def _classify(
        is_blocked: bool = False,
        unsupported: tuple[BucketReason, ...] = (),
        check: BucketBalanceCheck | None = DEFAULT_CHECK,
        derived: DerivedSnapshot | None = DEFAULT_DERIVED,
        is_derived_history_stale: bool = False,
        latest_observed_at: Timestamp | None = NOW,
        now: Timestamp = NOW,
) -> tuple[BucketStatus, tuple[BucketReason, ...]]:
    classification = classify_bucket(
        is_blocked=is_blocked,
        unsupported=unsupported,
        check=check,
        derived=derived,
        is_derived_history_stale=is_derived_history_stale,
        latest_observed_at=latest_observed_at,
        now=now,
        tolerance=TOLERANCE,
    )
    return classification.status, classification.reasons


def test_classifier_reconciled_and_mismatch() -> None:
    assert _classify() == (BucketStatus.RECONCILED, ())
    assert _classify(check=_check(observed_balance=3)) == (BucketStatus.MISMATCH, ())


def test_classifier_never_compared_is_pending() -> None:
    assert _classify(check=None) == (BucketStatus.PENDING, (BucketReason.NEVER_COMPARED,))


def test_classifier_blocked_overrides_and_keeps_underlying_reasons() -> None:
    assert _classify(is_blocked=True, check=None, derived=None) == (
        BucketStatus.BLOCKED, (BucketReason.NEVER_COMPARED,),
    )
    assert _classify(
        is_blocked=True,
        unsupported=(BucketReason.PROTOCOL_BUCKET,),
        is_derived_history_stale=True,
    ) == (BucketStatus.BLOCKED, (BucketReason.PROTOCOL_BUCKET, BucketReason.DERIVED_HISTORY_STALE))


def test_classifier_unsupported_beats_a_saved_match() -> None:
    assert _classify(unsupported=(BucketReason.QUERIES_DISABLED,)) == (
        BucketStatus.NOT_COMPARED, (BucketReason.QUERIES_DISABLED,),
    )


@pytest.mark.parametrize(('kwargs', 'reason'), [
    ({'is_derived_history_stale': True}, BucketReason.DERIVED_HISTORY_STALE),
    (
        {'derived': DerivedSnapshot(balance=FVal(6), latest_event_identifier=1)},
        BucketReason.DERIVED_SNAPSHOT_CHANGED,
    ),
    (
        {'derived': DerivedSnapshot(balance=FVal(5), latest_event_identifier=2)},
        BucketReason.DERIVED_SNAPSHOT_CHANGED,
    ),
    ({'derived': None}, BucketReason.DERIVED_SNAPSHOT_CHANGED),  # absent, never zero
    ({'latest_observed_at': Timestamp(NOW + 1)}, BucketReason.OBSERVATION_SUPERSEDED),
    ({'now': Timestamp(NOW + BALANCE_CHECK_MAX_AGE + 1)}, BucketReason.RESULT_EXPIRED),
])
def test_classifier_stale_saved_result_is_pending_even_if_it_was_a_mismatch(
        kwargs: dict[str, Any],
        reason: BucketReason,
) -> None:
    for observed in (5, 3):
        status, reasons = _classify(check=_check(observed_balance=observed), **kwargs)
        assert status == BucketStatus.PENDING
        assert reason in reasons


def test_classifier_old_observation_expires_even_when_compared_just_now() -> None:
    status, reasons = _classify(
        check=_check(observed_at=NOW - BALANCE_CHECK_MAX_AGE - 1),
        latest_observed_at=None,
    )
    assert (status, reasons) == (BucketStatus.PENDING, (BucketReason.RESULT_EXPIRED,))


def test_classifier_blocked_bucket_without_a_check_keeps_the_stale_reason() -> None:
    assert _classify(is_blocked=True, check=None, derived=None, is_derived_history_stale=True) == (
        BucketStatus.BLOCKED,
        (BucketReason.DERIVED_HISTORY_STALE, BucketReason.NEVER_COMPARED),
    )


# --- more plan 03 acceptance scenarios ----------------------------------------------------


def _stopped_bucket_with_metrics(database: DBHandler) -> None:
    _add_event(database, TEST_ADDR1, '5', 1000)
    _add_event(database, TEST_ADDR1, '8', 2000, HistoryEventType.SPEND)
    _process(database)
    assert _bucket_key() in _stops(database)


@pytest.mark.parametrize('state', ['dismissed', 'auto_remediating', 'unresolved'])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@with_accounts
def test_issue_state_never_changes_blockage(database: DBHandler, state: str) -> None:
    _stopped_bucket_with_metrics(database)
    manager = DataIssuesManager(database)
    issue = manager.list_issues(DataIssueFilters(kind=IssueKind.NEGATIVE_BALANCE))[0]
    if state == 'dismissed':
        manager.dismiss(issue.id)
    else:
        manager.update_state(issue.id, IssueState.AUTO_REMEDIATING)
        if state == 'unresolved':
            manager.update_state(issue.id, IssueState.UNRESOLVED)
    assert _bucket_key() in _stops(database)
    assert _make_detector(database, '5').run() == 0  # ADDR1 is skipped, ADDR2 has no metric
    assert _checks(database) == {}


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@with_accounts
def test_blocked_bucket_keeps_its_previous_check_untouched(database: DBHandler) -> None:
    _add_balance(database, TEST_ADDR1, '5')
    old = _check(observed_at=100, compared_at=200)
    _save(database, old)
    _stop(database)
    _make_detector(database, '5').run()
    assert _checks(database) == {old.key: old}


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@with_accounts
def test_failed_run_keeps_the_old_check(database: DBHandler) -> None:
    _add_balance(database, TEST_ADDR1, '5')
    old = _check(observed_at=100, compared_at=200)
    _save(database, old)
    with (
        patch.object(
            DataIssuesManager, 'report_current_balance_mismatch', side_effect=RuntimeError,
        ),
        pytest.raises(RuntimeError),
    ):
        _make_detector(database, '3').run()
    assert _checks(database) == {old.key: old}


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@with_accounts
def test_ordinary_reprocessing_keeps_unrelated_checks(database: DBHandler) -> None:
    _add_event(database, TEST_ADDR2, '5', 1000)
    _save(database, _check(TEST_ADDR2))
    _process(database)
    assert list(_checks(database)) == [(ETH_LOCATION, TEST_ADDR2, 'ETH')]


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@with_accounts
def test_eth2_stop_blocks_the_merged_eth_bucket_after_the_setting_is_turned_on(
        database: DBHandler,
) -> None:
    _add_balance(database, TEST_ADDR1, '5')
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT INTO bucket_processing_stops VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (ETH_LOCATION, TEST_ADDR1, '', 'ETH2', 1, 1000, '5', '-1'),
        )
        database.set_settings(write_cursor, ModifiableDBSettings(treat_eth2_as_eth=True))
    assert _make_detector(database, '3').run() == 0
    assert _checks(database) == {}


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@with_accounts
def test_asset_replacement_deletes_checks_of_both_assets_only(database: DBHandler) -> None:
    dai = 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F'
    for asset in ('ETH', 'BTC', dai):
        _save(database, _check(asset=asset))
    database.replace_asset_identifier(source_identifier='ETH', target_asset=Asset('BTC'))
    assert [key[2] for key in _checks(database)] == [dai]
