import threading
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.errors.misc import InputError, NotFoundError
from rotkehlchen.history.data_issues.constants import (
    IssueKind,
    IssueSeverity,
    IssueState,
)
from rotkehlchen.history.data_issues.manager import (
    MAX_REMEDIATION_ATTEMPTS,
    DataIssuesManager,
    _validate_state_transition,
)
from rotkehlchen.history.data_issues.types import DataIssueFilters
from rotkehlchen.locations.constants import (
    LOCATION_ETHEREUM,
)

pytestmark = pytest.mark.accounting_update

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def _write_negative_balance_issue(
        manager: DataIssuesManager,
        event_identifier: int = 1,
        location: str = LOCATION_ETHEREUM,
        location_label: str = '0x0000000000000000000000000000000000000001',
        protocol: str | None = None,
        asset: str = 'ETH',
        ts: int = 1000,
        balance_before: str = '1',
        negative_amount: str = '-1',
) -> int:
    return manager.write_issue(
        IssueKind.NEGATIVE_BALANCE,
        location=location,
        location_label=location_label,
        protocol=protocol,
        asset=asset,
        payload={
            'event_identifier': event_identifier,
            'in_memory_negative_amount': negative_amount,
            'derived_balance_before_event': balance_before,
        },
        ts_start=ts,
        ts_end=ts,
    )


def _write_current_balance_mismatch_issue(
        manager: DataIssuesManager,
        location: str = LOCATION_ETHEREUM,
        location_label: str = '0x0000000000000000000000000000000000000001',
        asset: str = 'ETH',
        derived_balance: str = '1',
        observed_balance: str = '2',
        delta: str = '1',
        latest_event_identifier: int | None = 1,
) -> int:
    return manager.write_issue(
        IssueKind.CURRENT_BALANCE_MISMATCH,
        location=location,
        location_label=location_label,
        protocol=None,
        asset=asset,
        payload={
            'derived_balance': derived_balance,
            'observed_balance': observed_balance,
            'delta': delta,
            'queried_at_ts': 2000,
            'latest_event_identifier': latest_event_identifier,
        },
        ts_start=1000,
        ts_end=2000,
    )


def _write_rebasing_issue(manager: DataIssuesManager, event_identifier: int = 1) -> int:
    return manager.write_issue(
        IssueKind.REBASING_TOKEN,
        location=LOCATION_ETHEREUM,
        location_label='0x0000000000000000000000000000000000000001',
        protocol=None,
        asset='eip155:1/erc20:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84',
        payload={
            'event_identifier': event_identifier,
            'block_number': 1,
            'reason': 'archive_node_unavailable',
        },
        ts_start=1000,
        ts_end=1000,
    )


def test_write_and_list_issues(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    issue_id = _write_negative_balance_issue(manager)

    issues = manager.list_issues()
    assert len(issues) == 1
    issue = issues[0]
    assert issue.id == issue_id
    assert issue.kind == IssueKind.NEGATIVE_BALANCE
    assert issue.state == IssueState.OPEN
    assert issue.severity == IssueSeverity.WARNING
    assert issue.payload['event_identifier'] == 1
    assert issue.payload['derived_balance_before_event'] == '1'
    assert issue.payload['in_memory_negative_amount'] == '-1'

    filtered = manager.list_issues(DataIssueFilters(
        kind=IssueKind.NEGATIVE_BALANCE,
        state=IssueState.OPEN,
        location=LOCATION_ETHEREUM,
        location_label='0x0000000000000000000000000000000000000001',
        asset='ETH',
    ))
    assert len(filtered) == 1
    assert filtered[0].id == issue_id


def test_invalid_amount_cleanup_keeps_issues_with_a_balance_stop(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    issue_ids = [manager.write_issue(
        kind=IssueKind.INVALID_EVENT_AMOUNT,
        location=LOCATION_ETHEREUM,
        location_label=label,
        protocol=None,
        asset='ETH',
        payload={'event_identifier': 1, 'amount': '-1'},
        ts_start=1000,
        ts_end=1000,
    ) for label in ('wallet with stop', 'wallet without stop')]
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT INTO bucket_processing_stops(location, location_label, asset, '
            'event_identifier, event_timestamp, derived_balance_before_event, negative_amount, '
            'issue_kind) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (LOCATION_ETHEREUM, 'wallet with stop', 'ETH', 1, 1000, '0', '-1',
             IssueKind.INVALID_EVENT_AMOUNT),
        )

    manager.resolve_event_issues_except(
        kind=IssueKind.INVALID_EVENT_AMOUNT,
        still_active_ids=set(),
    )

    assert [manager.get_issue(issue_id).state for issue_id in issue_ids] == [
        IssueState.OPEN, IssueState.RESOLVED,
    ]


def test_get_issue(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    issue_id = _write_negative_balance_issue(manager)
    issue = manager.get_issue(issue_id)
    assert issue.id == issue_id

    with pytest.raises(NotFoundError):
        manager.get_issue(issue_id + 1)


def test_state_transitions(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    issue_id = _write_negative_balance_issue(manager)

    issue = manager.update_state(issue_id, IssueState.AUTO_REMEDIATING, attempt={'step': 1})
    assert issue.state == IssueState.AUTO_REMEDIATING
    assert issue.auto_remediation_attempts == [{'step': 1}]
    assert issue.resolved_at is None

    issue = manager.update_state(issue_id, IssueState.RESOLVED, resolution={'result': 'ok'})
    assert issue.state == IssueState.RESOLVED
    assert issue.resolved_at is not None
    assert issue.payload['resolution'] == {'result': 'ok'}

    issue_id = _write_negative_balance_issue(manager, event_identifier=2)
    issue = manager.update_state(issue_id, IssueState.AUTO_REMEDIATING)
    issue = manager.update_state(issue_id, IssueState.UNRESOLVED)
    assert issue.state == IssueState.UNRESOLVED
    issue = manager.update_state(issue_id, IssueState.AUTO_REMEDIATING)
    assert issue.state == IssueState.AUTO_REMEDIATING
    # a run that attempted nothing hands the issue back to open
    issue = manager.update_state(issue_id, IssueState.OPEN)
    assert issue.state == IssueState.OPEN

    with pytest.raises(InputError):
        manager.update_state(issue_id, IssueState.UNRESOLVED)


def test_update_state_rejects_unexpected_state(database: DBHandler) -> None:
    """An update conditional on the state must not act on an issue that left that state."""
    manager = DataIssuesManager(database)
    manager.update_state(
        issue_id := _write_negative_balance_issue(manager),
        IssueState.AUTO_REMEDIATING,
        expected_state=IssueState.OPEN,
    )
    manager.resolve_manually(issue_id, note='done')

    with pytest.raises(InputError):  # resolved -> open is an allowed transition by itself
        manager.update_state(
            issue_id, IssueState.OPEN, expected_state=IssueState.AUTO_REMEDIATING,
        )
    assert (issue := manager.get_issue(issue_id)).state == IssueState.RESOLVED
    assert issue.payload['resolution'] == {'manual': True, 'note': 'done'}


def test_update_state_does_not_overwrite_concurrent_dismissal(database: DBHandler) -> None:
    """A dismissal attempted after update_state read the row, but before it wrote, must win.

    The dismissal is started from inside update_state, right after its read, and given
    time to land in that window. The issue must end up dismissed, never flipped back
    to resolved by the update's write.
    """
    manager = DataIssuesManager(database)
    manager.update_state(
        issue_id := _write_negative_balance_issue(manager),
        IssueState.AUTO_REMEDIATING,
    )
    dismissal_started = threading.Event()

    def dismiss() -> None:
        dismissal_started.set()
        manager.dismiss(issue_id)

    dismissal = threading.Thread(target=dismiss)

    def dismiss_after_read(current_state: str | IssueState, new_state: IssueState) -> None:
        if dismissal.ident is None:  # only the update's own validation opens the window
            dismissal.start()
            assert dismissal_started.wait(5)
            dismissal.join(0.5)
        _validate_state_transition(current_state, new_state)

    with patch(
        'rotkehlchen.history.data_issues.manager._validate_state_transition',
        side_effect=dismiss_after_read,
    ):
        manager.update_state(issue_id, IssueState.RESOLVED, resolution={'result': 'ok'})
        dismissal.join(5)

    assert dismissal.is_alive() is False
    assert (issue := manager.get_issue(issue_id)).state == IssueState.DISMISSED
    assert 'resolution' not in issue.payload


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('use_update_state', [True, False])
def test_only_latest_attempt_keeps_comparison(database: DBHandler, use_update_state: bool) -> None:
    manager = DataIssuesManager(database)
    issue_id = _write_negative_balance_issue(manager)
    old_attempt = {
        'strategy': 'test',
        'changed_transaction_count': 1,
        'transactions': [{'tx_hash': 'old'}],
    }
    manager.update_state(issue_id, IssueState.AUTO_REMEDIATING, attempt=old_attempt)
    new_attempt = {'strategy': 'test', 'transactions': [{'tx_hash': 'new'}]}
    if use_update_state:
        manager.update_state(issue_id, IssueState.UNRESOLVED, attempt=new_attempt)
    else:
        manager.append_auto_remediation_attempt(issue_id, attempt=new_attempt)
    assert manager.get_issue(issue_id).auto_remediation_attempts == [
        {'strategy': 'test', 'changed_transaction_count': 1}, new_attempt,
    ]
    manager.append_auto_remediation_attempt(issue_id, attempt={'strategy': 'failed'})
    assert all(
        'transactions' not in attempt
        for attempt in manager.get_issue(issue_id).auto_remediation_attempts
    )


def test_append_auto_remediation_attempt_caps_history(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    issue_id = _write_negative_balance_issue(manager)
    attempts = [{'step': step} for step in range(MAX_REMEDIATION_ATTEMPTS + 5)]

    for attempt in attempts:
        issue = manager.append_auto_remediation_attempt(issue_id, attempt=attempt)

    assert issue.auto_remediation_attempts == attempts[-MAX_REMEDIATION_ATTEMPTS:]
    assert manager.get_issue(issue_id).auto_remediation_attempts == (
        attempts[-MAX_REMEDIATION_ATTEMPTS:]
    )


def test_update_state_caps_remediation_history(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    issue_id = _write_negative_balance_issue(manager)
    attempts = [{'step': step} for step in range(MAX_REMEDIATION_ATTEMPTS + 5)]

    issue = manager.update_state(issue_id, IssueState.AUTO_REMEDIATING, attempt=attempts[0])
    for step, attempt in enumerate(attempts[1:], start=1):
        state = IssueState.UNRESOLVED if step % 2 == 1 else IssueState.AUTO_REMEDIATING
        issue = manager.update_state(issue_id, state, attempt=attempt)

    assert issue.auto_remediation_attempts == attempts[-MAX_REMEDIATION_ATTEMPTS:]


def test_retry_auto_remediation(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    issue_id = _write_rebasing_issue(manager)

    issue, should_schedule = manager.retry_auto_remediation(issue_id)
    assert should_schedule is True
    assert issue.state == IssueState.AUTO_REMEDIATING

    issue, should_schedule = manager.retry_auto_remediation(issue_id)
    assert should_schedule is False
    assert issue.state == IssueState.AUTO_REMEDIATING

    issue = manager.update_state(issue_id, IssueState.UNRESOLVED)
    issue, should_schedule = manager.retry_auto_remediation(issue.id)
    assert should_schedule is True
    assert issue.state == IssueState.AUTO_REMEDIATING

    issue = manager.append_auto_remediation_attempt(
        issue_id=issue_id,
        attempt={'strategy': 'test'},
        resolution={'reason': 'fixed'},
    )
    assert issue.auto_remediation_attempts == [{'strategy': 'test'}]
    assert issue.payload['resolution'] == {'reason': 'fixed'}

    unsupported_issue_id = _write_negative_balance_issue(manager, event_identifier=2)
    with pytest.raises(InputError, match='Auto-remediation is not supported'):
        manager.retry_auto_remediation(unsupported_issue_id)

    manager.update_state(unsupported_issue_id, IssueState.AUTO_REMEDIATING)
    with pytest.raises(InputError, match='Auto-remediation is not supported'):
        manager.retry_auto_remediation(unsupported_issue_id)


def test_reset_orphaned_remediations(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    issue_id = _write_rebasing_issue(manager)
    manager.retry_auto_remediation(issue_id)

    manager.reset_orphaned_remediations()

    issue, should_schedule = manager.retry_auto_remediation(issue_id)
    assert should_schedule is True
    assert issue.state == IssueState.AUTO_REMEDIATING


def test_resolve_superseded_negative_balance_issues(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    superseded_id = _write_negative_balance_issue(manager, event_identifier=1)
    unaffected_id = _write_negative_balance_issue(manager, event_identifier=2)
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'UPDATE data_issues SET asset=? WHERE id=?',
            ('OTHER_ASSET', unaffected_id),
        )

    manager.resolve_superseded_negative_balance_issues(assets=frozenset({'ETH'}))

    assert manager.get_issue(superseded_id).state == IssueState.RESOLVED
    assert manager.get_issue(unaffected_id).state == IssueState.OPEN


def test_dismiss_and_resolve_manually(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    issue_id = _write_negative_balance_issue(manager)

    issue = manager.dismiss(issue_id)
    assert issue.state == IssueState.DISMISSED

    with pytest.raises(InputError):
        manager.resolve_manually(issue_id, note='ignored')

    issue_id = _write_negative_balance_issue(manager, event_identifier=3)
    issue = manager.resolve_manually(issue_id, note='fixed manually')
    assert issue.state == IssueState.RESOLVED
    assert issue.payload['resolution'] == {'manual': True, 'note': 'fixed manually'}

    with pytest.raises(InputError):
        manager.resolve_manually(issue_id, note='updated')

    issue = manager.dismiss(issue_id)
    assert issue.state == IssueState.DISMISSED
    assert issue.resolved_at is None
    assert 'resolution' not in issue.payload


def test_write_issue_idempotency(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    issue_id = _write_negative_balance_issue(manager)
    same_id = _write_negative_balance_issue(
        manager,
        balance_before='2',
        negative_amount='-2',
    )
    assert same_id == issue_id
    assert len(manager.list_issues()) == 1
    assert manager.get_issue(issue_id).payload['derived_balance_before_event'] == '2'


def test_write_bucket_scoped_issue_idempotency(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    issue_id = _write_current_balance_mismatch_issue(manager)
    same_id = _write_current_balance_mismatch_issue(
        manager=manager,
        observed_balance='3',
        delta='2',
        latest_event_identifier=2,
    )
    assert same_id == issue_id
    assert len(manager.list_issues()) == 1
    assert manager.get_issue(issue_id).payload['observed_balance'] == '3'
    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT event_identifier FROM data_issues WHERE id = ?',
            (issue_id,),
        ).fetchone()[0] is None


def test_event_scoped_issue_uniqueness_uses_event_identifier(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    issue_id = _write_negative_balance_issue(manager, event_identifier=1)
    other_id = _write_negative_balance_issue(manager, event_identifier=2)
    assert other_id != issue_id
    assert len(manager.list_issues()) == 2


def test_write_issue_dismissed_not_reopened(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    issue_id = _write_negative_balance_issue(manager)
    manager.dismiss(issue_id)

    same_id = _write_negative_balance_issue(manager)
    assert same_id == issue_id
    assert manager.get_issue(issue_id).state == IssueState.DISMISSED


def test_write_issue_unchanged_candidate_keeps_manual_resolution(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    issue_id = _write_negative_balance_issue(manager)
    manager.resolve_manually(issue_id, note='checked')

    same_id = _write_negative_balance_issue(manager)
    assert same_id == issue_id
    issue = manager.get_issue(issue_id)
    assert issue.state == IssueState.RESOLVED
    assert issue.resolved_at is not None
    assert issue.payload['resolution'] == {'manual': True, 'note': 'checked'}


def test_write_issue_unchanged_candidate_reopens_automatic_resolution(
        database: DBHandler,
) -> None:
    """An automatically resolved issue must reopen when its candidate is rediscovered."""
    manager = DataIssuesManager(database)
    issue_id = _write_negative_balance_issue(manager)
    manager.update_state(issue_id, IssueState.AUTO_REMEDIATING)
    manager.update_state(
        issue_id,
        IssueState.RESOLVED,
        resolution={'attribution': 'system', 'strategy': 'redecode', 'notes': 'matched'},
    )

    same_id = _write_negative_balance_issue(manager)
    assert same_id == issue_id
    issue = manager.get_issue(issue_id)
    assert issue.state == IssueState.OPEN
    assert issue.resolved_at is None
    assert 'resolution' not in issue.payload


def test_write_issue_unchanged_candidate_reopens_system_resolution(database: DBHandler) -> None:
    """A system resolution (no resolution payload) must reopen when rediscovered."""
    manager = DataIssuesManager(database)
    location = LOCATION_ETHEREUM
    issue_id = _write_negative_balance_issue(manager, location=location)
    manager.resolve_event_issues(
        kind=IssueKind.NEGATIVE_BALANCE,
        issues=[(location, '0x0000000000000000000000000000000000000001', None, 'ETH', 1)],
    )
    assert manager.get_issue(issue_id).state == IssueState.RESOLVED

    same_id = _write_negative_balance_issue(manager, location=location)
    assert same_id == issue_id
    assert manager.get_issue(issue_id).state == IssueState.OPEN


def test_write_issue_changed_candidate_reopens_resolved(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    issue_id = _write_negative_balance_issue(manager)
    manager.resolve_manually(issue_id, note='checked')

    same_id = _write_negative_balance_issue(
        manager,
        balance_before='5',
        negative_amount='-5',
    )
    assert same_id == issue_id
    issue = manager.get_issue(issue_id)
    assert issue.state == IssueState.OPEN
    assert issue.resolved_at is None
    assert issue.payload['in_memory_negative_amount'] == '-5'
    assert 'resolution' not in issue.payload


def test_dismiss_not_found(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    with pytest.raises(NotFoundError):
        manager.dismiss(999)


def test_bulk_resolvers_only_touch_states_the_table_allows(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    open_id = _write_negative_balance_issue(manager, event_identifier=1)
    unresolved_id = _write_negative_balance_issue(manager, event_identifier=2)
    manager.update_state(unresolved_id, IssueState.AUTO_REMEDIATING)
    manager.update_state(unresolved_id, IssueState.UNRESOLVED)
    dismissed_id = _write_negative_balance_issue(manager, event_identifier=3)
    manager.dismiss(dismissed_id)

    manager.resolve_superseded_negative_balance_issues(frozenset({'ETH'}))

    assert manager.get_issue(open_id).state == IssueState.RESOLVED
    assert manager.get_issue(open_id).resolved_at is not None
    assert manager.get_issue(unresolved_id).state == IssueState.RESOLVED
    assert manager.get_issue(dismissed_id).state == IssueState.DISMISSED
    assert manager.get_issue(dismissed_id).resolved_at is None


def test_resolved_issue_reopens_through_the_table(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    issue_id = _write_negative_balance_issue(manager)
    manager.resolve_manually(issue_id)
    assert manager.get_issue(issue_id).resolved_at is not None

    assert manager.update_state(issue_id, IssueState.OPEN).resolved_at is None
    with pytest.raises(InputError):
        manager.update_state(issue_id, IssueState.UNRESOLVED)


def test_dismissed_is_terminal_and_dismiss_is_idempotent(database: DBHandler) -> None:
    manager = DataIssuesManager(database)
    issue_id = _write_negative_balance_issue(manager)
    dismissed = manager.dismiss(issue_id)

    assert manager.dismiss(issue_id) == dismissed
    for state in IssueState:
        with pytest.raises(InputError):
            manager.update_state(issue_id, state)


def test_resolve_unmatched_bridge_issues_except_keeps_unmatched_and_dismissed(
        database: DBHandler,
) -> None:
    manager = DataIssuesManager(database)
    ids = {}
    for event_identifier in (1, 2, 3):
        ids[event_identifier] = manager.write_issue(
            IssueKind.UNMATCHED_BRIDGE,
            location=LOCATION_ETHEREUM,
            location_label='0x0000000000000000000000000000000000000001',
            protocol=None,
            asset='ETH',
            payload={
                'event_identifier': event_identifier,
                'group_identifier': f'group-{event_identifier}',
                'direction': 'deposit',
            },
            ts_start=1000,
            ts_end=1000,
        )
    manager.dismiss(ids[3])

    manager.resolve_unmatched_bridge_issues_except(still_unmatched_ids={1})

    assert manager.get_issue(ids[1]).state == IssueState.OPEN
    assert manager.get_issue(ids[2]).state == IssueState.RESOLVED
    assert manager.get_issue(ids[3]).state == IssueState.DISMISSED


def test_reopen_manual_filter_disposition_and_from_ts_scoping(database: DBHandler) -> None:
    from rotkehlchen.db.cache import DBCacheStatic
    from rotkehlchen.db.filtering import DataIssuesFilterQuery
    from rotkehlchen.history.data_issues.actions import build_suggested_actions
    from rotkehlchen.history.data_issues.diagnostics import (
        explain_data_issue,
        serialize_issue,
    )

    manager = DataIssuesManager(database)
    mp_id = manager.write_issue(
        kind=IssueKind.MISSING_PRICE,
        location=LOCATION_ETHEREUM,
        location_label='0x0000000000000000000000000000000000000001',
        protocol=None,
        asset='ETH',
        payload={
            'event_identifier': 10,
            'group_identifier': 'grp-mp',
            'to_asset': 'USD',
            'amount': '1',
            'direction': 'spend',
        },
        ts_start=100_000,
        ts_end=100_000,
    )
    mcb_id = manager.write_issue(
        kind=IssueKind.MISSING_COST_BASIS,
        location=LOCATION_ETHEREUM,
        location_label='0x0000000000000000000000000000000000000001',
        protocol=None,
        asset='ETH',
        payload={
            'event_identifier': 11,
            'group_identifier': 'grp-mcb',
            'requested_amount': '3',
            'covered_amount': '1',
            'uncovered_amount': '2',
            'fallback_basis': '0',
        },
        ts_start=200_000,
        ts_end=200_000,
    )
    swap_id = manager.write_issue(
        kind=IssueKind.INCOMPLETE_SWAP,
        location=LOCATION_ETHEREUM,
        location_label='0x0000000000000000000000000000000000000001',
        protocol=None,
        asset='ETH',
        payload={
            'event_identifier': 12,
            'group_identifier': 'grp-swap',
            'event_identifiers': [12, 13],
            'present_legs': [{
                'event_identifier': 12,
                'subtype': 'spend',
                'asset': 'ETH',
                'amount': '1',
            }],
            'missing_or_excluded_reason': 'ignored_asset',
            'excluded_assets': ['DAI'],
        },
        ts_start=300_000,
        ts_end=300_000,
    )
    uet_id = manager.write_issue(
        kind=IssueKind.UNMATCHED_EXCHANGE_TRANSFER,
        location='kraken',
        location_label='Kraken',
        protocol=None,
        asset='ETH',
        payload={
            'event_identifier': 14,
            'group_identifier': 'grp-uet',
            'subtype': 'spend',
            'amount': '1',
        },
        ts_start=400_000,
        ts_end=400_000,
    )

    # Top-level event_identifier, group_identifier fallback, and dynamic suggested_actions.
    mp_issue = manager.get_issue(mp_id)
    assert mp_issue.event_identifier == 10
    assert mp_issue.group_identifier == 'grp-mp'
    assert [a['action'] for a in build_suggested_actions(mp_issue)] == [
        'set_manual_price', 'ignore_asset', 'ignore_action',
    ]
    mcb_actions = build_suggested_actions(manager.get_issue(mcb_id))
    assert [a['action'] for a in mcb_actions] == [
        'add_acquisition', 'match_transfer', 'confirm_zero_basis',
    ]
    assert mcb_actions[0]['params']['timestamp'] == 200_000  # milliseconds for CreateHistoryEvent
    assert 'entry_type' in mcb_actions[0]['requires_input']
    assert mcb_actions[1]['params'] == {'external': False}
    assert mcb_actions[2]['params'] == {'disposition': 'confirm_zero_basis'}
    swap_actions = build_suggested_actions(manager.get_issue(swap_id))
    assert [a['action'] for a in swap_actions] == [
        'ignore_group', 'unignore_asset', 'edit_event', 'dismiss_as_standalone',
    ]
    assert swap_actions[2]['params'] == {'identifier': 12, 'group_identifier': 'grp-swap'}
    assert swap_actions[3]['params'] == {'disposition': 'dismiss_as_standalone'}
    uet_actions = build_suggested_actions(manager.get_issue(uet_id))
    assert [a['action'] for a in uet_actions] == [
        'auto_match_exchange_transfer', 'manual_match_event', 'resolve_as_external',
    ]
    assert uet_actions[0]['params'] == {}
    assert uet_actions[1]['params'] == {'asset_movement': 14, 'external': False}
    assert len(serialize_issue(mp_issue)['suggested_actions']) == 3
    assert explain_data_issue(database, mcb_id)['facts']['uncovered_amount'] == '2'
    assert explain_data_issue(database, swap_id)['facts']['excluded_assets'] == ['DAI']
    assert explain_data_issue(database, uet_id)['facts']['subtype'] == 'spend'

    # retry_auto_remediation accepts UNMATCHED_EXCHANGE_TRANSFER.
    retrying, scheduled = manager.retry_auto_remediation(uet_id)
    assert scheduled is True
    assert retrying.state == IssueState.AUTO_REMEDIATING

    # resolve_manually with disposition + manual_only filter.
    confirmed = manager.resolve_manually(
        mcb_id,
        note='zero cost airdrop',
        disposition='confirm_zero_basis',
    )
    assert confirmed.payload['resolution'] == {
        'manual': True,
        'disposition': 'confirm_zero_basis',
        'note': 'zero cost airdrop',
    }
    assert build_suggested_actions(confirmed) == []

    # Auto-resolved issue must NOT appear in manual_only=True.
    manager.resolve_event_issues_except(
        kind=IssueKind.MISSING_PRICE,
        still_active_ids=set(),
        from_ts=200_000,  # mp_id is at 100_000 -> untouched!
    )
    assert manager.get_issue(mp_id).state == IssueState.OPEN
    manager.resolve_event_issues_except(
        kind=IssueKind.MISSING_PRICE,
        still_active_ids=set(),
        from_ts=100_000,  # now resolved automatically
    )
    assert manager.get_issue(mp_id).state == IssueState.RESOLVED

    manual_only_rows = manager.list_issues(DataIssuesFilterQuery.make(manual_only=True))
    assert [row.id for row in manual_only_rows] == [mcb_id]

    # Reopen from RESOLVED and DISMISSED, and confirm cost-basis staleness on INCOMPLETE_SWAP.
    reopened_mcb = manager.reopen(mcb_id)
    assert reopened_mcb.state == IssueState.OPEN
    assert reopened_mcb.resolved_at is None
    assert 'resolution' not in reopened_mcb.payload
    with pytest.raises(InputError):
        manager.reopen(mcb_id)

    manager.dismiss(swap_id)
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name = ?',
            (DBCacheStatic.STALE_COST_BASIS_FROM_TS.value,),
        )
    reopened_swap = manager.reopen(swap_id)
    assert reopened_swap.state == IssueState.OPEN
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor, DBCacheStatic.STALE_COST_BASIS_FROM_TS,
        ) == '300000'
