from __future__ import annotations

from time import monotonic
from typing import TYPE_CHECKING

import pytest

from rotkehlchen.concurrency import cancellable_sleep
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.remediation.base import (
    BaseRemediationStrategy,
    RemediationOutcome,
    RemediationPipeline,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.data_issues.types import DataIssue

pytestmark = pytest.mark.parametrize('use_clean_caching_directory', [True])


class StubStrategy(BaseRemediationStrategy):
    def __init__(
            self,
            name: str,
            outcome: RemediationOutcome,
            calls: list[str],
            timeout: float = 30,
            applicable: bool = True,
    ) -> None:
        self.name = name
        self.outcome = outcome
        self.calls = calls
        self.timeout = timeout
        self.applicable = applicable

    def applies_to(self, issue: DataIssue) -> bool:
        return self.applicable and issue.kind == IssueKind.NEGATIVE_BALANCE

    def attempt(self, issue: DataIssue) -> RemediationOutcome:
        self.calls.append(self.name)
        return self.outcome


class BlockingStrategy(StubStrategy):
    def attempt(self, issue: DataIssue) -> RemediationOutcome:
        self.calls.append(self.name)
        cancellable_sleep(10)
        return self.outcome


def _make_issue(database: DBHandler) -> DataIssue:
    manager = DataIssuesManager(database)
    issue_id = manager.write_issue(
        kind=IssueKind.NEGATIVE_BALANCE,
        location='f',
        location_label='0xaccount',
        protocol=None,
        asset='ETH',
        payload={
            'event_identifier': 1,
            'in_memory_negative_amount': '-1',
            'derived_balance_before_event': '0',
        },
        ts_start=1,
        ts_end=1,
    )
    return manager.get_issue(issue_id)


def test_pipeline_runs_strategies_in_order_until_success(database: DBHandler) -> None:
    calls: list[str] = []
    manager = DataIssuesManager(database)
    issue = _make_issue(database)
    RemediationPipeline(manager, (
        StubStrategy('first', RemediationOutcome(False, 'first_failed', ''), calls),
        StubStrategy('second', RemediationOutcome(True, 'second_succeeded', ''), calls),
    )).run(issue)

    issue = manager.get_issue(issue.id)
    assert calls == ['first', 'second']
    assert issue.state == IssueState.RESOLVED
    assert [attempt['strategy'] for attempt in issue.auto_remediation_attempts] == [
        'first',
        'second',
    ]


def test_pipeline_cancels_strategy_when_its_budget_expires(database: DBHandler) -> None:
    calls: list[str] = []
    manager = DataIssuesManager(database)
    issue = _make_issue(database)
    started_at = monotonic()
    RemediationPipeline(manager, (
        BlockingStrategy('slow', RemediationOutcome(True, 'too_late', ''), calls, timeout=0.1),
        StubStrategy('fallback', RemediationOutcome(True, 'fallback_succeeded', ''), calls),
    )).run(issue)

    issue = manager.get_issue(issue.id)
    assert monotonic() - started_at < 1
    assert calls == ['slow', 'fallback']
    assert issue.state == IssueState.RESOLVED
    assert issue.auto_remediation_attempts[0]['attribution'] == 'timeout'


def test_pipeline_leaves_inapplicable_issue_unchanged(database: DBHandler) -> None:
    calls: list[str] = []
    issue = _make_issue(database)
    strategy = StubStrategy(
        'unused',
        RemediationOutcome(True, 'unused', ''),
        calls,
        applicable=False,
    )

    RemediationPipeline(DataIssuesManager(database), (strategy,)).run(issue)

    assert DataIssuesManager(database).get_issue(issue.id).state == IssueState.OPEN
    assert calls == []
