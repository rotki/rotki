from typing import TYPE_CHECKING

import pytest

from rotkehlchen.errors.misc import InputError, NotFoundError
from rotkehlchen.history.data_issues.constants import (
    IssueKind,
    IssueSeverity,
    IssueState,
)
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.types import DataIssueFilters
from rotkehlchen.types import Location

pytestmark = pytest.mark.accounting_update

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def _write_negative_balance_issue(
        manager: DataIssuesManager,
        event_identifier: int = 1,
        location: str = Location.ETHEREUM.serialize_for_db(),
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


def test_write_and_list_issues(database: 'DBHandler') -> None:
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
        location=Location.ETHEREUM.serialize_for_db(),
        location_label='0x0000000000000000000000000000000000000001',
        asset='ETH',
    ))
    assert len(filtered) == 1
    assert filtered[0].id == issue_id


def test_get_issue(database: 'DBHandler') -> None:
    manager = DataIssuesManager(database)
    issue_id = _write_negative_balance_issue(manager)
    issue = manager.get_issue(issue_id)
    assert issue.id == issue_id

    with pytest.raises(NotFoundError):
        manager.get_issue(issue_id + 1)


def test_state_transitions(database: 'DBHandler') -> None:
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

    with pytest.raises(InputError):
        manager.update_state(issue_id, IssueState.OPEN)


def test_dismiss_and_resolve_manually(database: 'DBHandler') -> None:
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


def test_write_issue_idempotency(database: 'DBHandler') -> None:
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


def test_write_issue_dismissed_not_reopened(database: 'DBHandler') -> None:
    manager = DataIssuesManager(database)
    issue_id = _write_negative_balance_issue(manager)
    manager.dismiss(issue_id)

    same_id = _write_negative_balance_issue(manager)
    assert same_id == issue_id
    assert manager.get_issue(issue_id).state == IssueState.DISMISSED


def test_write_issue_resolved_reopened(database: 'DBHandler') -> None:
    manager = DataIssuesManager(database)
    issue_id = _write_negative_balance_issue(manager)
    manager.resolve_manually(issue_id)

    same_id = _write_negative_balance_issue(manager)
    assert same_id == issue_id
    issue = manager.get_issue(issue_id)
    assert issue.state == IssueState.OPEN
    assert issue.resolved_at is None


def test_dismiss_not_found(database: 'DBHandler') -> None:
    manager = DataIssuesManager(database)
    with pytest.raises(NotFoundError):
        manager.dismiss(999)
