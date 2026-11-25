from contextlib import suppress
from dataclasses import replace
from typing import TYPE_CHECKING, Any, Final
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.chain.ethereum.constants import CPT_KRAKEN
from rotkehlchen.concurrency import TaskCancelledError
from rotkehlchen.constants.assets import A_ETH, A_USDC
from rotkehlchen.constants.timing import DAY_IN_SECONDS, HOUR_IN_SECONDS
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HistoryMappingState
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings, ModifiableDBSettings
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.remediation.base import RemediationPipeline
from rotkehlchen.history.data_issues.remediation.cex_matching import (
    ATTRIBUTION_MATCHED_DEPOSIT,
    ATTRIBUTION_MATCHED_WITHDRAWAL,
    CEX_ONCHAIN_MATCHING,
    CexOnchainMatchingStrategy,
    CexOnchainMatchVerificationStrategy,
    reprocess_balances_for_pending_matches,
)
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import (
    LOCATION_BINANCE,
    LOCATION_ETHEREUM,
    LOCATION_KRAKEN,
)
from rotkehlchen.tasks.data_issues import (
    REDECODE_CUSTOMIZED_TRANSACTIONS,
    run_data_issue_remediation,
)
from rotkehlchen.tasks.events import get_unmatched_asset_movements, match_asset_movements
from rotkehlchen.tasks.historical_balances import process_historical_balances
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1, TEST_ADDR2
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EventMetricKey,
    EvmTransaction,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_now_in_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.data_issues.types import DataIssue

pytestmark = [
    pytest.mark.accounting_update,
    pytest.mark.parametrize('use_clean_caching_directory', [True]),
]

ONCHAIN_TS: Final = TimestampMS(1_700_000_000_000)
CEX_MATCHING_MODULE: Final = 'rotkehlchen.history.data_issues.remediation.cex_matching'


def _add_kraken_withdrawal_issue(
        database: DBHandler,
        onchain_amount: str = '1',
        seconds_between_legs: int = 60,
        onchain_ts: TimestampMS = ONCHAIN_TS,
        address: ChecksumEvmAddress = TEST_ADDR1,
) -> tuple[DataIssue, int]:
    """Save a Kraken withdrawal of 1 ETH and its onchain leg, and return the issue it causes.

    The onchain leg is saved the way the decoder leaves it before any matching: a withdrawal
    from Kraken, which takes the ETH out of the wallet and so drives its balance negative.
    """
    movement_ts = onchain_ts - seconds_between_legs * 1000
    with database.user_write() as write_cursor:
        (events_db := DBHistoryEvents(database)).add_history_events(write_cursor, [HistoryEvent(
            group_identifier=f'kraken-funding-{onchain_ts}',
            sequence_index=0,
            timestamp=TimestampMS(movement_ts - 1000),
            location=LOCATION_KRAKEN,
            location_label='Kraken',
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(1),
        ), AssetMovement(
            unique_id=f'kraken-withdrawal-{onchain_ts}',
            timestamp=TimestampMS(movement_ts),
            location=LOCATION_KRAKEN,
            location_label='Kraken',
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal(1),
        )])
        onchain_event_id = events_db.add_history_event(write_cursor, EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=onchain_ts,
            location=LOCATION_ETHEREUM,
            location_label=address,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            amount=FVal(onchain_amount),
            counterparty=CPT_KRAKEN,
        ))

    assert onchain_event_id is not None
    process_historical_balances(database, database.msg_aggregator)
    issues = [
        issue for issue in DataIssuesManager(database).list_issues()
        if issue.payload.get('event_identifier') == onchain_event_id
    ]
    assert [(issue.kind, issue.location) for issue in issues] == [
        (IssueKind.NEGATIVE_BALANCE, LOCATION_ETHEREUM),
    ]
    return issues[0], onchain_event_id


def _set_matching_settings(database: DBHandler, **settings: Any) -> None:
    with database.user_write() as write_cursor:
        database.set_settings(write_cursor, ModifiableDBSettings(**settings))


def _run_strategy(database: DBHandler, issue: DataIssue) -> DataIssue:
    """Run the matching, reprocessing and verification passes of a remediation on one issue."""
    manager = DataIssuesManager(database)
    RemediationPipeline(
        manager=manager,
        strategies=(CexOnchainMatchingStrategy(database),),
    ).run(issue)
    reprocess_balances_for_pending_matches(
        database=database,
        chains_aggregator=MagicMock(),
        issues=[manager.get_issue(issue.id)],
    )
    RemediationPipeline(
        manager=manager,
        strategies=(CexOnchainMatchVerificationStrategy(database),),
    ).run(manager.get_issue(issue.id))
    return manager.get_issue(issue.id)


def _attributions(issue: DataIssue) -> list[str]:
    return [attempt['attribution'] for attempt in issue.auto_remediation_attempts]


def _get_onchain_event_state(database: DBHandler, event_id: int) -> tuple[str, str, list[str]]:
    """Type and subtype of the onchain event and the balances written for it."""
    with database.conn.read_ctx() as cursor:
        event_type, event_subtype = cursor.execute(
            'SELECT type, subtype FROM history_events WHERE identifier=?', (event_id,),
        ).fetchone()
        return event_type, event_subtype, [row[0] for row in cursor.execute(
            'SELECT metric_value FROM event_metrics WHERE event_identifier=? AND metric_key=?',
            (event_id, EventMetricKey.BALANCE.serialize()),
        )]


@pytest.mark.parametrize(('onchain_amount', 'tolerance', 'should_resolve'), [
    ('1', None, True),
    ('0.99', None, False),
    ('0.99', FVal('0.02'), True),
])
def test_matching_exchange_withdrawal_resolves_negative_wallet_balance(
        database: DBHandler,
        onchain_amount: str,
        tolerance: FVal | None,
        should_resolve: bool,
) -> None:
    """The onchain leg only pairs up within the amount tolerance saved in the DB settings."""
    issue, onchain_event_id = _add_kraken_withdrawal_issue(database, onchain_amount)
    if tolerance is not None:
        _set_matching_settings(database, asset_movement_amount_tolerance=tolerance)

    issue = _run_strategy(database, issue)
    if should_resolve is False:
        assert issue.state == IssueState.UNRESOLVED
        assert [(x['strategy'], x['attribution'], x['success']) for x in issue.auto_remediation_attempts] == [  # noqa: E501
            (CEX_ONCHAIN_MATCHING, 'no_match', False),
        ]
        assert _get_onchain_event_state(database, onchain_event_id) == ('withdrawal', 'remove asset', [])  # noqa: E501
        return

    assert issue.state == IssueState.RESOLVED
    assert issue.payload['resolution']['strategy'] == CEX_ONCHAIN_MATCHING
    assert issue.payload['resolution']['attribution'] == ATTRIBUTION_MATCHED_WITHDRAWAL
    assert [(x['attribution'], x['success']) for x in issue.auto_remediation_attempts] == [
        ('reprocessing_pending', False),
        (ATTRIBUTION_MATCHED_WITHDRAWAL, True),
    ]
    assert _get_onchain_event_state(database, onchain_event_id) == (
        'exchange transfer', 'receive', [onchain_amount],
    )


@pytest.mark.parametrize(('time_range', 'should_resolve'), [
    (None, False),
    (HOUR_IN_SECONDS * 48, True),
])
def test_movement_is_only_considered_within_the_configured_time_range(
        database: DBHandler,
        time_range: int | None,
        should_resolve: bool,
) -> None:
    issue, onchain_event_id = _add_kraken_withdrawal_issue(
        database=database,
        seconds_between_legs=HOUR_IN_SECONDS * 30,
    )
    if time_range is not None:
        _set_matching_settings(database, asset_movement_time_range=time_range)

    assert CexOnchainMatchingStrategy(database).applies_to(issue) is should_resolve
    issue = _run_strategy(database, issue)
    if should_resolve:
        assert issue.state == IssueState.RESOLVED
        assert _get_onchain_event_state(database, onchain_event_id)[:2] == ('exchange transfer', 'receive')  # noqa: E501
    else:  # an issue the strategy does not apply to is left exactly as it was
        assert issue.state == IssueState.OPEN
        assert issue.auto_remediation_attempts == []
        assert _get_onchain_event_state(database, onchain_event_id)[:2] == ('withdrawal', 'remove asset')  # noqa: E501


@pytest.mark.parametrize(('issue_changes', 'applies'), [
    ({}, True),
    ({'asset': A_USDC.identifier}, False),
    ({'location_label': ''}, False),
    ({'kind': IssueKind.REBASING_TOKEN}, False),
    ({'kind': IssueKind.CURRENT_BALANCE_MISMATCH}, True),
    ({'location': LOCATION_KRAKEN, 'location_label': 'Kraken'}, True),
    ({
        'location': LOCATION_KRAKEN,
        'location_label': 'Kraken',
        'kind': IssueKind.CURRENT_BALANCE_MISMATCH,
    }, True),
    ({
        'location': LOCATION_KRAKEN,
        'location_label': 'Kraken',
        'kind': IssueKind.UNMATCHED_BRIDGE,
    }, False),
    ({'location': LOCATION_KRAKEN, 'location_label': 'Other Kraken'}, False),
    ({'location': LOCATION_BINANCE, 'location_label': 'Kraken'}, False),
    ({'location': 'external'}, False),
])
def test_applies_only_to_issues_an_unmatched_movement_could_explain(
        database: DBHandler,
        issue_changes: dict[str, Any],
        applies: bool,
) -> None:
    issue, _ = _add_kraken_withdrawal_issue(database)
    strategy = CexOnchainMatchingStrategy(database)
    assert strategy.applies_to(replace(issue, **issue_changes)) is applies


@pytest.mark.parametrize(('has_matching_capability', 'expected_state'), [
    (True, IssueState.RESOLVED),
    (False, IssueState.OPEN),
])
def test_remediation_run_matches_only_with_the_premium_capability(
        database: DBHandler,
        has_matching_capability: bool,
        expected_state: IssueState,
) -> None:
    issue, onchain_event_id = _add_kraken_withdrawal_issue(database)
    chains_aggregator = MagicMock()
    chains_aggregator.premium.fetch_limits.return_value = {
        'asset_movement_matching': has_matching_capability,
    }
    run_data_issue_remediation(database=database, chains_aggregator=chains_aggregator)
    assert DataIssuesManager(database).get_issue(issue.id).state == expected_state
    assert _get_onchain_event_state(database, onchain_event_id)[:2] == (
        ('exchange transfer', 'receive') if has_matching_capability else
        ('withdrawal', 'remove asset')
    )


@pytest.mark.parametrize('observed_balance', ['1', '2'])
@pytest.mark.parametrize('later_receive', [False, True])
def test_exchange_deposit_only_resolves_matching_observed_balance(
        database: DBHandler,
        observed_balance: str,
        later_receive: bool,
) -> None:
    """Pairing must remove the reported mismatch, not merely create an event link."""
    with database.user_write() as cursor:
        (events_db := DBHistoryEvents(database)).add_history_events(cursor, [HistoryEvent(
            group_identifier='wallet-funding',
            sequence_index=0,
            timestamp=TimestampMS(ONCHAIN_TS - 1000),
            location=LOCATION_ETHEREUM,
            location_label=TEST_ADDR1,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(2),
        ), AssetMovement(
            unique_id='kraken-deposit',
            timestamp=TimestampMS(ONCHAIN_TS + 60_000),
            location=LOCATION_KRAKEN,
            location_label='Kraken',
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal(1),
        )])
        event_id = events_db.add_history_event(cursor, EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ONCHAIN_TS,
            location=LOCATION_ETHEREUM,
            location_label=TEST_ADDR1,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            amount=FVal(1),
            counterparty=CPT_KRAKEN,
        ))
    assert event_id is not None
    if later_receive:
        with database.user_write() as cursor:
            events_db.add_history_event(cursor, HistoryEvent(
                group_identifier='future-receive',
                sequence_index=0,
                timestamp=TimestampMS(ONCHAIN_TS + 172_800_000),
                location=LOCATION_ETHEREUM,
                location_label=TEST_ADDR1,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal(5),
            ))
    process_historical_balances(database, database.msg_aggregator)
    manager = DataIssuesManager(database)
    issue_id = manager.write_issue(
        kind=IssueKind.CURRENT_BALANCE_MISMATCH,
        location=LOCATION_ETHEREUM,
        location_label=TEST_ADDR1,
        protocol=None,
        asset=A_ETH.identifier,
        payload={
            'derived_balance': '3',
            'observed_balance': observed_balance,
            'delta': str(FVal(observed_balance) - 3),
            'queried_at_ts': ONCHAIN_TS // 1000,
            'latest_event_identifier': event_id,
        },
        ts_start=ONCHAIN_TS,
        ts_end=ONCHAIN_TS,
    )
    issue = _run_strategy(database, manager.get_issue(issue_id))
    assert _get_onchain_event_state(database, event_id) == ('exchange transfer', 'spend', ['1'])
    if observed_balance == '1':
        assert issue.state == IssueState.RESOLVED
        assert issue.payload['resolution']['attribution'] == ATTRIBUTION_MATCHED_DEPOSIT
    else:
        assert issue.state == IssueState.UNRESOLVED
        assert issue.auto_remediation_attempts[-1]['attribution'] == 'matched_without_resolving'


def test_pending_processing_is_retried_after_the_movement_is_already_matched(
        database: DBHandler,
) -> None:
    issue, event_id = _add_kraken_withdrawal_issue(database)
    with patch(f'{CEX_MATCHING_MODULE}.process_historical_balances', return_value=None):
        run_data_issue_remediation(database, MagicMock())

    manager = DataIssuesManager(database)
    pending = manager.get_issue(issue.id)
    assert pending.state == IssueState.OPEN
    assert _attributions(pending) == ['reprocessing_pending']
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(cursor, DBCacheStatic.STALE_BALANCES_FROM_TS) is not None
    run_data_issue_remediation(database, MagicMock())
    resolved = manager.get_issue(issue.id)
    assert resolved.state == IssueState.RESOLVED
    assert _attributions(resolved) == ['reprocessing_pending', ATTRIBUTION_MATCHED_WITHDRAWAL]
    assert _get_onchain_event_state(database, event_id) == ('exchange transfer', 'receive', ['1'])


def test_match_cancelled_before_verification_is_verified_on_the_next_run(
        database: DBHandler,
) -> None:
    issue, event_id = _add_kraken_withdrawal_issue(database)
    with (
        patch(
            f'{CEX_MATCHING_MODULE}.process_historical_balances',
            side_effect=TaskCancelledError('logout'),
        ),
        suppress(TaskCancelledError),
    ):
        run_data_issue_remediation(database, MagicMock())

    manager = DataIssuesManager(database)
    assert _get_onchain_event_state(database, event_id)[:2] == ('exchange transfer', 'receive')
    assert _attributions(cancelled := manager.get_issue(issue.id)) == ['reprocessing_pending']
    assert cancelled.auto_remediation_attempts[0]['matched_movement_ids'] == (
        cancelled.auto_remediation_attempts[0]['movement_ids']
    )

    run_data_issue_remediation(database, MagicMock())
    resolved = manager.get_issue(issue.id)
    assert resolved.state == IssueState.RESOLVED
    assert _attributions(resolved) == ['reprocessing_pending', ATTRIBUTION_MATCHED_WITHDRAWAL]


def test_match_orphaned_by_a_crash_is_verified_after_an_earlier_attempt(
        database: DBHandler,
) -> None:
    """A verification owed by an issue that already had attempts survives the orphan reset."""
    issue, _ = _add_kraken_withdrawal_issue(database, onchain_amount='0.99')
    manager = DataIssuesManager(database)
    run_data_issue_remediation(database, MagicMock())
    assert _attributions(manager.get_issue(issue.id)) == ['no_match']

    _set_matching_settings(database, asset_movement_amount_tolerance=FVal('0.02'))
    with (
        patch(
            f'{CEX_MATCHING_MODULE}.process_historical_balances',
            side_effect=TaskCancelledError('crash'),
        ),
        suppress(TaskCancelledError),
    ):
        run_data_issue_remediation(database, MagicMock())
    with database.user_write() as write_cursor:  # the process died while verifying
        write_cursor.execute(
            'UPDATE data_issues SET state = ? WHERE id = ?',
            (IssueState.AUTO_REMEDIATING, issue.id),
        )
    manager.reset_orphaned_remediations()
    assert manager.get_issue(issue.id).state == IssueState.UNRESOLVED

    run_data_issue_remediation(database, MagicMock())
    resolved = manager.get_issue(issue.id)
    assert resolved.state == IssueState.RESOLVED
    assert _attributions(resolved) == [
        'no_match',
        'reprocessing_pending',
        ATTRIBUTION_MATCHED_WITHDRAWAL,
    ]


def test_verification_retry_without_pending_edits_does_not_reprocess(
        database: DBHandler,
) -> None:
    """A cut-off reprocessing keeps the stale marker, so the balances it deleted are rebuilt.

    Once a scheduled pass rebuilt them, the owed verification only rechecks the condition.
    """
    issue, _ = _add_kraken_withdrawal_issue(database)
    with (
        patch('rotkehlchen.tasks.historical_balances.METRICS_BATCH_SIZE', 1),
        patch(
            'rotkehlchen.tasks.historical_balances.checkpoint',
            side_effect=TaskCancelledError('budget'),
        ),
        suppress(TaskCancelledError),
    ):
        run_data_issue_remediation(database, MagicMock())

    with database.conn.read_ctx() as cursor:
        assert (stale_from_ts := database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_BALANCES_FROM_TS,
        )) is not None
    process_historical_balances(
        database=database,
        msg_aggregator=database.msg_aggregator,
        from_ts=TimestampMS(int(stale_from_ts)),
    )
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(cursor, DBCacheStatic.STALE_BALANCES_FROM_TS) is None

    with patch(f'{CEX_MATCHING_MODULE}.process_historical_balances') as reprocess:
        run_data_issue_remediation(database, MagicMock())
    reprocess.assert_not_called()
    resolved = DataIssuesManager(database).get_issue(issue.id)
    assert resolved.state == IssueState.RESOLVED
    assert _attributions(resolved) == ['reprocessing_pending', ATTRIBUTION_MATCHED_WITHDRAWAL]


def test_successful_matching_does_not_hide_a_remaining_negative_balance(
        database: DBHandler,
) -> None:
    issue, event_id = _add_kraken_withdrawal_issue(database)
    with database.user_write() as cursor:
        DBHistoryEvents(database).add_history_event(cursor, HistoryEvent(
            group_identifier='earlier-wallet-spend',
            sequence_index=0,
            timestamp=TimestampMS(ONCHAIN_TS - 1000),
            location=LOCATION_ETHEREUM,
            location_label=TEST_ADDR1,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(2),
        ))
    issue = _run_strategy(database, issue)
    assert issue.state == IssueState.UNRESOLVED
    assert issue.auto_remediation_attempts[-1]['attribution'] == 'matched_without_resolving'
    assert _get_onchain_event_state(database, event_id) == ('exchange transfer', 'receive', [])


def test_matching_leaves_movements_outside_the_issue_window_untouched(
        database: DBHandler,
) -> None:
    issue, _ = _add_kraken_withdrawal_issue(database)
    with database.user_write() as cursor:
        events_db = DBHistoryEvents(database)
        movement_id = events_db.add_history_event(cursor, AssetMovement(
            unique_id='outside-window',
            timestamp=(outside_ts := TimestampMS(ONCHAIN_TS + HOUR_IN_SECONDS * 1000 * 21)),
            location=LOCATION_KRAKEN,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal(2),
        ))
        event_id = events_db.add_history_event(cursor, EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=TimestampMS(outside_ts + 1000),
            location=LOCATION_ETHEREUM,
            location_label=TEST_ADDR1,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(2),
        ))
    assert event_id is not None
    assert _run_strategy(database, issue).state == IssueState.RESOLVED
    assert _get_onchain_event_state(database, event_id)[:2] == ('receive', 'none')
    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM history_event_links '
            'WHERE left_event_id=? OR right_event_id=?',
            (movement_id, movement_id),
        ).fetchone()[0] == 0


def test_exchange_issue_without_unmatched_movements_stays_open(database: DBHandler) -> None:
    with database.user_write() as cursor:
        event_id = DBHistoryEvents(database).add_history_event(cursor, HistoryEvent(
            group_identifier='kraken-spend',
            sequence_index=0,
            timestamp=ONCHAIN_TS,
            location=LOCATION_KRAKEN,
            location_label='Kraken',
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(1),
        ))
    assert event_id is not None
    process_historical_balances(database, database.msg_aggregator)
    manager = DataIssuesManager(database)
    issue = manager.list_issues()[0]
    assert CexOnchainMatchingStrategy(database).applies_to(issue) is False

    issue = _run_strategy(database, issue)
    assert issue.state == IssueState.OPEN
    assert issue.auto_remediation_attempts == []


def test_onchain_issue_with_movement_consumed_earlier_in_run_stays_open(
        database: DBHandler,
) -> None:
    issue1, _ = _add_kraken_withdrawal_issue(database)
    with database.user_write() as cursor:
        DBHistoryEvents(database).add_history_event(cursor, EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=TimestampMS(ONCHAIN_TS - 1000),
            location=LOCATION_ETHEREUM,
            location_label=TEST_ADDR2,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(2),
        ))
    process_historical_balances(database, database.msg_aggregator)
    manager = DataIssuesManager(database)
    issues = manager.list_issues()
    assert len(issues) == 2
    issue2 = next(entry for entry in issues if entry.id != issue1.id)

    run_data_issue_remediation(database, MagicMock())
    assert manager.get_issue(issue1.id).state == IssueState.RESOLVED
    refetched_issue2 = manager.get_issue(issue2.id)
    assert refetched_issue2.state == IssueState.OPEN
    assert refetched_issue2.auto_remediation_attempts == []


def test_open_issue_ignores_already_linked_movement_in_window(database: DBHandler) -> None:
    with database.user_write() as cursor:
        (events_db := DBHistoryEvents(database)).add_history_events(cursor, [HistoryEvent(
            group_identifier='wallet2-funding',
            sequence_index=0,
            timestamp=TimestampMS(ONCHAIN_TS - 120_000),
            location=LOCATION_ETHEREUM,
            location_label=TEST_ADDR2,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(2),
        ), AssetMovement(
            unique_id='kraken-deposit-already-linked',
            timestamp=TimestampMS(ONCHAIN_TS - 90_000),
            location=LOCATION_KRAKEN,
            location_label='Kraken',
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal(1),
        ), EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=TimestampMS(ONCHAIN_TS - 100_000),
            location=LOCATION_ETHEREUM,
            location_label=TEST_ADDR2,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            amount=FVal(1),
            counterparty=CPT_KRAKEN,
        )])
    match_asset_movements(database=database)

    with database.user_write() as cursor:
        events_db.add_history_event(cursor, HistoryEvent(
            group_identifier='kraken-spend-open',
            sequence_index=0,
            timestamp=TimestampMS(ONCHAIN_TS - 1000),
            location=LOCATION_KRAKEN,
            location_label='Kraken',
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(2),
        ))
    process_historical_balances(database, database.msg_aggregator)
    manager = DataIssuesManager(database)
    exchange_issue = manager.list_issues()[0]
    exchange_issue = _run_strategy(database, exchange_issue)
    assert exchange_issue.state == IssueState.OPEN
    assert exchange_issue.auto_remediation_attempts == []

    with database.user_write() as cursor:
        events_db.add_history_events(cursor, [HistoryEvent(
            group_identifier='kraken-funding-new',
            sequence_index=0,
            timestamp=TimestampMS(ONCHAIN_TS - 61_000),
            location=LOCATION_KRAKEN,
            location_label='Kraken',
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(2),
        ), AssetMovement(
            unique_id='kraken-withdrawal-new',
            timestamp=TimestampMS(ONCHAIN_TS - 60_000),
            location=LOCATION_KRAKEN,
            location_label='Kraken',
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal(1),
        )])
        onchain_event_id = events_db.add_history_event(cursor, EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ONCHAIN_TS,
            location=LOCATION_ETHEREUM,
            location_label=TEST_ADDR1,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            amount=FVal(1),
            counterparty=CPT_KRAKEN,
        ))
    process_historical_balances(database, database.msg_aggregator)
    onchain_issue = next(
        entry for entry in manager.list_issues()
        if entry.payload.get('event_identifier') == onchain_event_id
    )
    resolved = _run_strategy(database, onchain_issue)
    assert resolved.state == IssueState.RESOLVED
    assert resolved.payload['resolution']['attribution'] == ATTRIBUTION_MATCHED_WITHDRAWAL
    assert resolved.payload['resolution']['notes'] == (
        'Matched 1 exchange movements with their onchain events'
    )


def test_matched_without_resolving_after_reprocessing_pending_is_not_retried(
        database: DBHandler,
) -> None:
    issue, _ = _add_kraken_withdrawal_issue(database)
    with database.user_write() as cursor:
        DBHistoryEvents(database).add_history_event(cursor, HistoryEvent(
            group_identifier='earlier-wallet-spend',
            sequence_index=0,
            timestamp=TimestampMS(ONCHAIN_TS - 1000),
            location=LOCATION_ETHEREUM,
            location_label=TEST_ADDR1,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(2),
        ))

    with patch(f'{CEX_MATCHING_MODULE}.process_historical_balances', return_value=None):
        run_data_issue_remediation(database, MagicMock())

    manager = DataIssuesManager(database)
    assert _attributions(manager.get_issue(issue.id)) == ['reprocessing_pending']

    run_data_issue_remediation(database, MagicMock())
    after_second_run = manager.get_issue(issue.id)
    assert after_second_run.state == IssueState.UNRESOLVED
    assert [entry['attribution'] for entry in after_second_run.auto_remediation_attempts] == [
        'reprocessing_pending',
        'matched_without_resolving',
    ]
    assert CexOnchainMatchingStrategy(database).applies_to(after_second_run) is False

    run_data_issue_remediation(database, MagicMock())
    assert len(manager.get_issue(issue.id).auto_remediation_attempts) == 2


def test_multiple_matched_movements_attribute_negative_balance_to_causal_link(
        database: DBHandler,
) -> None:
    with database.user_write() as cursor:
        (events_db := DBHistoryEvents(database)).add_history_events(cursor, [HistoryEvent(
            group_identifier='wallet1-funding',
            sequence_index=0,
            timestamp=TimestampMS(ONCHAIN_TS - 200_000),
            location=LOCATION_ETHEREUM,
            location_label=TEST_ADDR1,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(5),
        ), AssetMovement(
            unique_id='kraken-deposit-earlier',
            timestamp=TimestampMS(ONCHAIN_TS - 110_000),
            location=LOCATION_KRAKEN,
            location_label='Kraken',
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal(5),
        ), EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=TimestampMS(ONCHAIN_TS - 100_000),
            location=LOCATION_ETHEREUM,
            location_label=TEST_ADDR1,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            amount=FVal(5),
            counterparty=CPT_KRAKEN,
        ), HistoryEvent(
            group_identifier='kraken-funding',
            sequence_index=0,
            timestamp=TimestampMS(ONCHAIN_TS - 70_000),
            location=LOCATION_KRAKEN,
            location_label='Kraken',
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(11),
        ), AssetMovement(
            unique_id='kraken-withdrawal-causal',
            timestamp=TimestampMS(ONCHAIN_TS - 60_000),
            location=LOCATION_KRAKEN,
            location_label='Kraken',
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal(11),
        )])
        onchain_event_id = events_db.add_history_event(cursor, EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ONCHAIN_TS,
            location=LOCATION_ETHEREUM,
            location_label=TEST_ADDR1,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            amount=FVal(11),
            counterparty=CPT_KRAKEN,
        ))
    assert onchain_event_id is not None
    process_historical_balances(database, database.msg_aggregator)
    issues = DataIssuesManager(database).list_issues()
    assert [(issue.kind, issue.payload['event_identifier']) for issue in issues] == [
        (IssueKind.NEGATIVE_BALANCE, onchain_event_id),
    ]

    resolved = _run_strategy(database, issues[0])
    assert resolved.state == IssueState.RESOLVED
    assert resolved.payload['resolution']['attribution'] == ATTRIBUTION_MATCHED_WITHDRAWAL
    assert resolved.payload['resolution']['notes'] == (
        'Matched 2 exchange movements with their onchain events'
    )


def test_stale_balances_after_reprocessing_returns_reprocessing_pending_and_retries(
        database: DBHandler,
) -> None:
    issue, event_id = _add_kraken_withdrawal_issue(database)

    def process_and_mark_stale(**kwargs: Any) -> bool:
        assert process_historical_balances(**kwargs) is True
        with database.user_write() as write_cursor:
            database.set_static_cache(
                write_cursor=write_cursor,
                name=DBCacheStatic.STALE_BALANCES_FROM_TS,
                value=str(ONCHAIN_TS),
            )
            database.set_static_cache(
                write_cursor=write_cursor,
                name=DBCacheStatic.STALE_BALANCES_MODIFICATION_TS,
                value=str(ts_now_in_ms()),
            )
        return True

    with patch(
        f'{CEX_MATCHING_MODULE}.process_historical_balances',
        side_effect=process_and_mark_stale,
    ):
        run_data_issue_remediation(database, MagicMock())

    manager = DataIssuesManager(database)
    pending = manager.get_issue(issue.id)
    assert pending.state == IssueState.OPEN
    assert _attributions(pending) == ['reprocessing_pending']

    run_data_issue_remediation(database, MagicMock())
    resolved = manager.get_issue(issue.id)
    assert resolved.state == IssueState.RESOLVED
    assert resolved.auto_remediation_attempts[-1]['attribution'] == ATTRIBUTION_MATCHED_WITHDRAWAL
    assert _get_onchain_event_state(database, event_id) == ('exchange transfer', 'receive', ['1'])


def test_links_not_made_by_the_strategy_are_never_credited(database: DBHandler) -> None:
    """An unresolved issue without attempts whose window holds a link made elsewhere."""
    issue, event_id = _add_kraken_withdrawal_issue(database)
    match_asset_movements(database=database)
    process_historical_balances(database, database.msg_aggregator)
    assert _get_onchain_event_state(database, event_id) == ('exchange transfer', 'receive', ['1'])
    with database.user_write() as write_cursor:  # e.g. reset while another strategy ran
        write_cursor.execute(
            'UPDATE data_issues SET state = ? WHERE id = ?',
            (IssueState.UNRESOLVED, issue.id),
        )

    run_data_issue_remediation(database, MagicMock())
    after = DataIssuesManager(database).get_issue(issue.id)
    assert after.state == IssueState.UNRESOLVED
    assert after.auto_remediation_attempts == []


def test_issues_matched_in_one_run_share_one_reprocessing(database: DBHandler) -> None:
    first, _ = _add_kraken_withdrawal_issue(database)
    second, _ = _add_kraken_withdrawal_issue(
        database=database,
        onchain_ts=TimestampMS(ONCHAIN_TS + DAY_IN_SECONDS * 10 * 1000),
        address=TEST_ADDR2,
    )
    with (
        patch(
            f'{CEX_MATCHING_MODULE}.process_historical_balances',
            wraps=process_historical_balances,
        ) as reprocess,
        patch(
            f'{CEX_MATCHING_MODULE}.get_unmatched_asset_movements',
            wraps=get_unmatched_asset_movements,
        ) as load_unmatched,
    ):
        run_data_issue_remediation(database, MagicMock())

    assert reprocess.call_count == 1
    assert load_unmatched.call_count == 1
    manager = DataIssuesManager(database)
    for issue in (first, second):
        assert _attributions(manager.get_issue(issue.id)) == [
            'reprocessing_pending',
            ATTRIBUTION_MATCHED_WITHDRAWAL,
        ]


@pytest.mark.parametrize(('state', 'latest_attribution'), [
    (IssueState.OPEN, 'timeout'),
    (IssueState.UNRESOLVED, 'no_match'),
])
def test_applies_to_never_reads_the_database(
        database: DBHandler,
        state: IssueState,
        latest_attribution: str,
) -> None:
    """Inputs the strategy did not preload when it was created are left to `attempt`."""
    issue, _ = _add_kraken_withdrawal_issue(database)
    strategy = CexOnchainMatchingStrategy(database)
    issue = replace(issue, state=state, auto_remediation_attempts=[{
        'attribution': latest_attribution,
        'strategy': CEX_ONCHAIN_MATCHING,
        'timestamp': 0,
        'success': False,
    }])
    with patch.object(database.conn, 'read_ctx', side_effect=AssertionError('unexpected DB read')):
        assert strategy.applies_to(issue) is True


@pytest.mark.parametrize((
    'onchain_amount',
    'expected_state',
    'expected_attribution',
    'expected_success',
    'expected_reason',
), [
    (
        '0.99',
        IssueState.UNRESOLVED,
        'no_match',
        False,
        'No exchange movement in the issue window could be matched',
    ),
    (
        '1',
        IssueState.RESOLVED,
        ATTRIBUTION_MATCHED_WITHDRAWAL,
        True,
        'Matched 1 exchange movements with their onchain events',
    ),
])
def test_stored_attempt_schema_includes_trial_snapshot(
        database: DBHandler,
        onchain_amount: str,
        expected_state: IssueState,
        expected_attribution: str,
        expected_success: bool,
        expected_reason: str,
) -> None:
    issue, _ = _add_kraken_withdrawal_issue(database, onchain_amount=onchain_amount)
    with database.conn.read_ctx() as cursor:
        movement_id = cursor.execute(
            "SELECT identifier FROM history_events WHERE type = 'exchange transfer'",
        ).fetchone()[0]

    issue = _run_strategy(database, issue)
    assert issue.state == expected_state
    *earlier_attempts, attempt = issue.auto_remediation_attempts
    if expected_success:  # the matches owed a verification before it resolved the issue
        assert [(x['attribution'], x['matched_movement_ids']) for x in earlier_attempts] == [
            ('reprocessing_pending', [movement_id]),
        ]
        assert all(earlier_attempts[0][key] == attempt[key] for key in (
            'amount_tolerance', 'time_range', 'movement_ids', 'window_fingerprint',
        ))
    else:
        assert earlier_attempts == []
    settings = CachedSettings().get_settings()
    assert set(attempt) == {
        'attribution',
        'strategy',
        'timestamp',
        'success',
        'reason',
        'amount_tolerance',
        'time_range',
        'movement_ids',
        'window_fingerprint',
    }
    assert attempt['strategy'] == CEX_ONCHAIN_MATCHING
    assert attempt['attribution'] == expected_attribution
    assert attempt['success'] is expected_success
    assert attempt['reason'] == expected_reason
    assert attempt['amount_tolerance'] == str(settings.asset_movement_amount_tolerance)
    assert attempt['time_range'] == settings.asset_movement_time_range
    assert attempt['movement_ids'] == [movement_id]
    assert isinstance(attempt['window_fingerprint'], str)
    assert len(attempt['window_fingerprint']) == 32


def test_unresolved_no_match_skips_unchanged_and_retries_when_counterpart_added(
        database: DBHandler,
) -> None:
    with database.user_write() as cursor:
        (events_db := DBHistoryEvents(database)).add_history_events(cursor, [HistoryEvent(
            group_identifier='kraken-funding',
            sequence_index=0,
            timestamp=TimestampMS(ONCHAIN_TS - 70_000),
            location=LOCATION_KRAKEN,
            location_label='Kraken',
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(1),
        ), AssetMovement(
            unique_id='kraken-withdrawal',
            timestamp=TimestampMS(ONCHAIN_TS - 60_000),
            location=LOCATION_KRAKEN,
            location_label='Kraken',
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal(1),
        ), HistoryEvent(
            group_identifier='wallet-spend',
            sequence_index=0,
            timestamp=ONCHAIN_TS,
            location=LOCATION_ETHEREUM,
            location_label=TEST_ADDR1,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(1),
        )])
    process_historical_balances(database, database.msg_aggregator)
    manager = DataIssuesManager(database)
    issue = manager.list_issues()[0]

    run_data_issue_remediation(database, MagicMock())
    after_first = manager.get_issue(issue.id)
    assert after_first.state == IssueState.UNRESOLVED
    assert [a['attribution'] for a in after_first.auto_remediation_attempts] == ['no_match']

    strategy = CexOnchainMatchingStrategy(database)
    with patch.object(database.conn, 'read_ctx', side_effect=AssertionError('unexpected DB read')):
        assert strategy.applies_to(after_first) is False
    with patch.object(DataIssuesManager, 'update_state', wraps=manager.update_state) as spy_update:
        run_data_issue_remediation(database, MagicMock())
    spy_update.assert_not_called()
    assert len(manager.get_issue(issue.id).auto_remediation_attempts) == 1

    with database.user_write() as cursor:
        counterpart_id = events_db.add_history_event(cursor, EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=TimestampMS(ONCHAIN_TS - 50_000),
            location=LOCATION_ETHEREUM,
            location_label=TEST_ADDR1,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            amount=FVal(1),
            counterparty=CPT_KRAKEN,
        ))
    assert counterpart_id is not None

    assert CexOnchainMatchingStrategy(database).applies_to(after_first) is True
    run_data_issue_remediation(database, MagicMock())
    resolved = manager.get_issue(issue.id)
    assert resolved.state == IssueState.RESOLVED
    attempts = resolved.auto_remediation_attempts
    assert _attributions(resolved) == [
        'no_match',
        'reprocessing_pending',
        ATTRIBUTION_MATCHED_WITHDRAWAL,
    ]
    assert attempts[0]['movement_ids'] == attempts[-1]['movement_ids']
    assert attempts[0]['window_fingerprint'] != attempts[-1]['window_fingerprint']


def test_unresolved_no_match_retries_when_new_cex_movement_added(database: DBHandler) -> None:
    with database.user_write() as cursor:
        (events_db := DBHistoryEvents(database)).add_history_events(cursor, [HistoryEvent(
            group_identifier='kraken-funding',
            sequence_index=0,
            timestamp=TimestampMS(ONCHAIN_TS - 80_000),
            location=LOCATION_KRAKEN,
            location_label='Kraken',
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(10),
        ), AssetMovement(
            unique_id='kraken-withdrawal-other',
            timestamp=TimestampMS(ONCHAIN_TS - 60_000),
            location=LOCATION_KRAKEN,
            location_label='Kraken',
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal(5),
        ), EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ONCHAIN_TS,
            location=LOCATION_ETHEREUM,
            location_label=TEST_ADDR1,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            amount=FVal(1),
            counterparty=CPT_KRAKEN,
        )])
    process_historical_balances(database, database.msg_aggregator)
    manager = DataIssuesManager(database)
    issue = manager.list_issues()[0]

    run_data_issue_remediation(database, MagicMock())
    assert manager.get_issue(issue.id).state == IssueState.UNRESOLVED
    with patch.object(DataIssuesManager, 'update_state', wraps=manager.update_state) as spy_update:
        run_data_issue_remediation(database, MagicMock())
    spy_update.assert_not_called()

    with database.user_write() as cursor:
        new_movement_id = events_db.add_history_event(cursor, AssetMovement(
            unique_id='kraken-withdrawal-matching',
            timestamp=TimestampMS(ONCHAIN_TS - 30_000),
            location=LOCATION_KRAKEN,
            location_label='Kraken',
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal(1),
        ))
    assert new_movement_id is not None

    run_data_issue_remediation(database, MagicMock())
    resolved = manager.get_issue(issue.id)
    assert resolved.state == IssueState.RESOLVED
    attempts = resolved.auto_remediation_attempts
    assert _attributions(resolved) == [
        'no_match',
        'reprocessing_pending',
        ATTRIBUTION_MATCHED_WITHDRAWAL,
    ]
    assert new_movement_id in attempts[-1]['movement_ids']
    assert len(attempts[-1]['movement_ids']) == 2


def test_unresolved_no_match_retries_when_amount_tolerance_widened(database: DBHandler) -> None:
    issue, _ = _add_kraken_withdrawal_issue(database, onchain_amount='0.99')
    manager = DataIssuesManager(database)

    run_data_issue_remediation(database, MagicMock())
    assert manager.get_issue(issue.id).state == IssueState.UNRESOLVED
    with patch.object(DataIssuesManager, 'update_state', wraps=manager.update_state) as spy_update:
        run_data_issue_remediation(database, MagicMock())
    spy_update.assert_not_called()
    assert len(manager.get_issue(issue.id).auto_remediation_attempts) == 1

    _set_matching_settings(database, asset_movement_amount_tolerance=FVal('0.02'))
    run_data_issue_remediation(database, MagicMock())
    resolved = manager.get_issue(issue.id)
    assert resolved.state == IssueState.RESOLVED
    attempts = resolved.auto_remediation_attempts
    assert _attributions(resolved) == [
        'no_match',
        'reprocessing_pending',
        ATTRIBUTION_MATCHED_WITHDRAWAL,
    ]
    assert attempts[-1]['amount_tolerance'] == '0.02'
    assert attempts[0]['amount_tolerance'] != attempts[-1]['amount_tolerance']


@pytest.mark.parametrize('deferred_reason', ['no_movement', 'no_premium'])
def test_unresolved_from_customized_redecode_is_resolved_without_rerunning_redecode(
        database: DBHandler,
        deferred_reason: str,
) -> None:
    customized_tx_hash = make_evm_tx_hash()
    customized_receive = EvmEvent(
        tx_ref=customized_tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(ONCHAIN_TS - 10_000),
        location=LOCATION_ETHEREUM,
        location_label=TEST_ADDR1,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=FVal(1),
        notes='customized receive',
    )
    events_db = DBHistoryEvents(database)
    with database.user_write() as cursor:
        DBEvmTx(database).add_transactions(
            write_cursor=cursor,
            evm_transactions=[EvmTransaction(
                tx_hash=customized_tx_hash,
                chain_id=ChainID.ETHEREUM,
                timestamp=Timestamp((ONCHAIN_TS - 10_000) // 1000),
                block_number=1,
                from_address=TEST_ADDR2,
                to_address=TEST_ADDR1,
                value=10**18,
                gas=21_000,
                gas_price=0,
                gas_used=0,
                input_data=b'',
                nonce=0,
            )],
            relevant_address=TEST_ADDR1,
        )
        events_db.add_history_event(
            write_cursor=cursor,
            event=customized_receive,
            mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED},
        )
        events_db.add_history_event(cursor, EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ONCHAIN_TS,
            location=LOCATION_ETHEREUM,
            location_label=TEST_ADDR1,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            amount=FVal(2),
            counterparty=CPT_KRAKEN,
        ))
        if deferred_reason == 'no_premium':
            events_db.add_history_events(cursor, [HistoryEvent(
                group_identifier='kraken-funding',
                sequence_index=0,
                timestamp=TimestampMS(ONCHAIN_TS - 70_000),
                location=LOCATION_KRAKEN,
                location_label='Kraken',
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal(2),
            ), AssetMovement(
                unique_id='kraken-withdrawal',
                timestamp=TimestampMS(ONCHAIN_TS - 60_000),
                location=LOCATION_KRAKEN,
                location_label='Kraken',
                event_subtype=HistoryEventSubType.SPEND,
                asset=A_ETH,
                amount=FVal(2),
            )])

    process_historical_balances(database, database.msg_aggregator)
    manager = DataIssuesManager(database)
    issue = manager.list_issues()[0]
    chains_aggregator = MagicMock()
    chains_aggregator.premium.fetch_limits.return_value = {
        'asset_movement_matching': deferred_reason != 'no_premium',
    }

    with patch(
        'rotkehlchen.tasks.data_issues.preview_transaction',
        return_value=[customized_receive],
    ) as preview:
        run_data_issue_remediation(database, chains_aggregator)
        after_redecode = manager.get_issue(issue.id)
        assert after_redecode.state == IssueState.UNRESOLVED
        assert [a['strategy'] for a in after_redecode.auto_remediation_attempts] == [
            REDECODE_CUSTOMIZED_TRANSACTIONS,
        ]
        assert preview.call_count == 1

        if deferred_reason == 'no_premium':
            chains_aggregator.premium.fetch_limits.return_value = {'asset_movement_matching': True}
        else:
            with database.user_write() as cursor:
                events_db.add_history_events(cursor, [HistoryEvent(
                    group_identifier='kraken-funding',
                    sequence_index=0,
                    timestamp=TimestampMS(ONCHAIN_TS - 70_000),
                    location=LOCATION_KRAKEN,
                    location_label='Kraken',
                    event_type=HistoryEventType.RECEIVE,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_ETH,
                    amount=FVal(2),
                ), AssetMovement(
                    unique_id='kraken-withdrawal',
                    timestamp=TimestampMS(ONCHAIN_TS - 60_000),
                    location=LOCATION_KRAKEN,
                    location_label='Kraken',
                    event_subtype=HistoryEventSubType.SPEND,
                    asset=A_ETH,
                    amount=FVal(2),
                )])

        run_data_issue_remediation(database, chains_aggregator)
        assert preview.call_count == 1

    resolved = manager.get_issue(issue.id)
    assert resolved.state == IssueState.RESOLVED
    assert [(a['strategy'], a['attribution']) for a in resolved.auto_remediation_attempts] == [
        (REDECODE_CUSTOMIZED_TRANSACTIONS, 'system'),
        (CEX_ONCHAIN_MATCHING, 'reprocessing_pending'),
        (CEX_ONCHAIN_MATCHING, ATTRIBUTION_MATCHED_WITHDRAWAL),
    ]
    assert resolved.payload['resolution']['strategy'] == CEX_ONCHAIN_MATCHING


def test_newer_unrelated_issue_first_records_pending_verification_on_affected_issue(
        database: DBHandler,
) -> None:
    """Matching triggered by a newer unrelated issue must credit the older affected issue."""
    older_issue, _ = _add_kraken_withdrawal_issue(database)
    with database.user_write() as cursor:
        DBHistoryEvents(database).add_history_event(cursor, EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=TimestampMS(ONCHAIN_TS + 1000),
            location=LOCATION_ETHEREUM,
            location_label=TEST_ADDR2,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(2),
        ))
    process_historical_balances(database, database.msg_aggregator)
    manager = DataIssuesManager(database)
    issues = manager.list_issues()
    assert len(issues) == 2
    newer_issue = issues[0]
    assert newer_issue.id != older_issue.id  # newer ts_start is listed and processed first

    run_data_issue_remediation(database, MagicMock())
    resolved_older = manager.get_issue(older_issue.id)
    assert resolved_older.state == IssueState.RESOLVED
    assert _attributions(resolved_older) == [
        'reprocessing_pending',
        ATTRIBUTION_MATCHED_WITHDRAWAL,
    ]
    refetched_newer = manager.get_issue(newer_issue.id)
    assert refetched_newer.state == IssueState.OPEN
    assert refetched_newer.auto_remediation_attempts == []


def test_cross_bucket_match_handles_remaining_unmatched_movement_on_trigger_issue(
        database: DBHandler,
) -> None:
    older_issue, _ = _add_kraken_withdrawal_issue(database)
    with database.user_write() as cursor:
        events_db = DBHistoryEvents(database)
        events_db.add_history_event(cursor, EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=TimestampMS(ONCHAIN_TS + 1000),
            location=LOCATION_ETHEREUM,
            location_label=TEST_ADDR2,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(2),
        ))
        events_db.add_history_event(cursor, HistoryEvent(
            group_identifier='kraken-unmatched-funding',
            sequence_index=0,
            timestamp=TimestampMS(ONCHAIN_TS - 35_000),
            location=LOCATION_KRAKEN,
            location_label='Kraken',
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(99),
        ))
        unmatched_id = events_db.add_history_event(cursor, AssetMovement(
            unique_id='kraken-unmatched-other',
            timestamp=TimestampMS(ONCHAIN_TS - 30_000),
            location=LOCATION_KRAKEN,
            location_label='Kraken',
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal(99),
        ))
    assert unmatched_id is not None
    process_historical_balances(database, database.msg_aggregator)
    manager = DataIssuesManager(database)
    newer_issue = manager.list_issues()[0]
    assert newer_issue.id != older_issue.id

    run_data_issue_remediation(database, MagicMock())
    assert manager.get_issue(older_issue.id).state == IssueState.RESOLVED
    refetched_newer = manager.get_issue(newer_issue.id)
    assert refetched_newer.state == IssueState.UNRESOLVED
    assert _attributions(refetched_newer) == ['no_match']
    assert refetched_newer.auto_remediation_attempts[-1]['movement_ids'] == [unmatched_id]


def test_single_match_affects_multiple_issues_in_same_bucket(database: DBHandler) -> None:
    nb_issue, _ = _add_kraken_withdrawal_issue(database)
    manager = DataIssuesManager(database)
    mismatch_id = manager.write_issue(
        kind=IssueKind.CURRENT_BALANCE_MISMATCH,
        location=LOCATION_ETHEREUM,
        location_label=TEST_ADDR1,
        protocol=None,
        asset=A_ETH.identifier,
        payload={
            'derived_balance': '0',
            'observed_balance': '1',
            'delta': '1',
            'queried_at_ts': (ONCHAIN_TS + 1000) // 1000,
            'latest_event_identifier': None,
        },
        ts_start=ONCHAIN_TS + 1000,
        ts_end=ONCHAIN_TS + 1000,
    )

    run_data_issue_remediation(database, MagicMock())
    assert manager.get_issue(nb_issue.id).state == IssueState.RESOLVED
    assert _attributions(manager.get_issue(nb_issue.id)) == [
        'reprocessing_pending',
        ATTRIBUTION_MATCHED_WITHDRAWAL,
    ]
    resolved_mismatch = manager.get_issue(mismatch_id)
    assert resolved_mismatch.state == IssueState.RESOLVED
    assert _attributions(resolved_mismatch) == [
        'reprocessing_pending',
        ATTRIBUTION_MATCHED_WITHDRAWAL,
    ]


def test_unmatched_exchange_transfer_issue_auto_remediated_and_resolved(
        database: DBHandler,
) -> None:
    """UNMATCHED_EXCHANGE_TRANSFER issues are matched directly by CexOnchainMatchingStrategy and
    verified as RESOLVED once the ASSET_MOVEMENT_MATCH link is written."""
    from rotkehlchen.tasks.data_issues import retry_unmatched_exchange_transfer_issue

    _nb_issue, _onchain_event_id = _add_kraken_withdrawal_issue(database)
    unmatched_movements, _ = get_unmatched_asset_movements(database)
    movement = unmatched_movements[0]
    assert movement.identifier is not None
    manager = DataIssuesManager(database)
    uet_id = manager.write_issue(
        kind=IssueKind.UNMATCHED_EXCHANGE_TRANSFER,
        location=LOCATION_KRAKEN,
        location_label='Kraken',
        protocol=None,
        asset=A_ETH.identifier,
        payload={
            'event_identifier': movement.identifier,
            'group_identifier': movement.group_identifier,
            'subtype': 'spend',
            'amount': '1',
        },
        ts_start=movement.timestamp,
        ts_end=movement.timestamp,
    )
    issue, scheduled = manager.retry_auto_remediation(uet_id)
    assert scheduled is True
    assert issue.state == IssueState.AUTO_REMEDIATING

    from rotkehlchen.types import Price

    with patch('rotkehlchen.tasks.cost_basis.PriceHistorian') as historian:
        historian.return_value.query_historical_price.return_value = Price(FVal(2000))
        retry_unmatched_exchange_transfer_issue(
            database=database,
            chains_aggregator=MagicMock(),
            issue_id=uet_id,
        )
    resolved = manager.get_issue(uet_id)
    assert resolved.state == IssueState.RESOLVED
    assert _attributions(resolved) == [
        'reprocessing_pending',
        ATTRIBUTION_MATCHED_WITHDRAWAL,
    ]


def test_retry_unmatched_exchange_transfer_recovers_from_cancellation(database: DBHandler) -> None:
    """If remediation raises TaskCancelledError or an unexpected error, the issue transitions
    from AUTO_REMEDIATING -> UNRESOLVED instead of sticking in AUTO_REMEDIATING."""
    from rotkehlchen.tasks.data_issues import retry_unmatched_exchange_transfer_issue

    manager = DataIssuesManager(database)
    uet_id = manager.write_issue(
        kind=IssueKind.UNMATCHED_EXCHANGE_TRANSFER,
        location=LOCATION_KRAKEN,
        location_label='Kraken',
        protocol=None,
        asset=A_ETH.identifier,
        payload={
            'event_identifier': 999,
            'group_identifier': 'kraken-cancel',
            'subtype': 'spend',
            'amount': '1',
        },
        ts_start=ONCHAIN_TS,
        ts_end=ONCHAIN_TS,
    )
    manager.retry_auto_remediation(uet_id)

    with (
        patch(
            'rotkehlchen.tasks.data_issues.CexOnchainMatchingStrategy',
            side_effect=TaskCancelledError('cancelled'),
        ),
        pytest.raises(TaskCancelledError),
    ):
        retry_unmatched_exchange_transfer_issue(
            database=database,
            chains_aggregator=MagicMock(),
            issue_id=uet_id,
        )

    failed = manager.get_issue(uet_id)
    assert failed.state == IssueState.UNRESOLVED
    assert failed.auto_remediation_attempts[-1]['reason'] == 'processing_cancelled'
