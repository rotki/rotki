from __future__ import annotations

import logging
from functools import partial
from time import monotonic
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest

from rotkehlchen.concurrency import Task, TaskCancelledError, cancellable_sleep
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.remediation.base import (
    BaseRemediationStrategy,
    RemediationOutcome,
    RemediationPipeline,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.data_issues.types import DataIssue

pytestmark = [
    pytest.mark.accounting_update,
    pytest.mark.parametrize('use_clean_caching_directory', [True]),
]


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


class FailingStrategy(StubStrategy):
    def attempt(self, issue: DataIssue) -> RemediationOutcome:
        self.calls.append(self.name)
        raise RuntimeError('strategy failed unexpectedly')


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
    assert issue.payload['resolution'] == {
        'attribution': 'second_succeeded',
        'notes': '',
        'strategy': 'second',
    }


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


def test_pipeline_marks_issue_unresolved_when_strategy_fails(database: DBHandler) -> None:
    calls: list[str] = []
    manager = DataIssuesManager(database)
    issue = _make_issue(database)

    with pytest.raises(RuntimeError, match='strategy failed unexpectedly'):
        RemediationPipeline(manager, (
            FailingStrategy('failing', RemediationOutcome(False, 'failed', ''), calls),
        )).run(issue)

    assert calls == ['failing']
    assert manager.get_issue(issue.id).state == IssueState.UNRESOLVED


def test_pipeline_records_every_exhausted_attempt(
        database: DBHandler,
        caplog: pytest.LogCaptureFixture,
) -> None:
    calls: list[str] = []
    manager = DataIssuesManager(database)
    issue = _make_issue(database)
    caplog.set_level(logging.DEBUG, logger='rotkehlchen.history.data_issues.remediation.base')

    RemediationPipeline(manager, (
        StubStrategy('first', RemediationOutcome(False, 'system', 'first_failed'), calls),
        StubStrategy('second', RemediationOutcome(False, 'system', 'second_failed'), calls),
    )).run(issue)

    issue = manager.get_issue(issue.id)
    assert calls == ['first', 'second']
    assert issue.state == IssueState.UNRESOLVED
    assert [attempt['strategy'] for attempt in issue.auto_remediation_attempts] == [
        'first',
        'second',
    ]
    logged_strategies = [
        record.message.split("'strategy': ")[1].split(',', maxsplit=1)[0]
        for record in caplog.records
    ]
    assert logged_strategies == [
        "'first'",
        "'second'",
    ]


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


@pytest.mark.parametrize('error_type', [RemoteError, DeserializationError, InputError])
@pytest.mark.parametrize('fallback', [False, True])
def test_pipeline_records_operational_failure_and_continues(
        database: DBHandler,
        error_type: type[Exception],
        fallback: bool,
) -> None:
    """Record operational errors and either run the fallback or leave the issue unresolved."""
    calls: list[str] = []
    manager = DataIssuesManager(database)
    issue = _make_issue(database)
    failing = StubStrategy('failing', RemediationOutcome(False, 'system', ''), calls)
    strategies: tuple[BaseRemediationStrategy, ...] = (failing,)
    if fallback:
        strategies += (StubStrategy('fallback', RemediationOutcome(True, 'system', ''), calls),)

    with patch.object(failing, 'attempt', side_effect=error_type('receipt unavailable')):
        RemediationPipeline(manager, strategies).run(issue)

    issue = manager.get_issue(issue.id)
    assert issue.state == (IssueState.RESOLVED if fallback else IssueState.UNRESOLVED)
    assert calls == (['fallback'] if fallback else [])
    assert len(issue.auto_remediation_attempts) == (2 if fallback else 1)
    attempt = issue.auto_remediation_attempts[0]
    assert attempt['strategy'] == 'failing'
    assert attempt['success'] is False
    assert attempt['attribution'] == 'strategy_failed'
    assert attempt['reason'] == 'receipt unavailable'


def test_pipeline_propagates_cancellation_without_running_fallback(database: DBHandler) -> None:
    """Propagate cancellation without running the fallback or recording a normal failure."""
    calls: list[str] = []
    manager = DataIssuesManager(database)
    issue = _make_issue(database)
    cancelled = StubStrategy('cancelled', RemediationOutcome(False, 'system', ''), calls)
    with (
        patch.object(cancelled, 'attempt', side_effect=TaskCancelledError('cancelled')),
        pytest.raises(TaskCancelledError),
    ):
        RemediationPipeline(manager, (
            cancelled,
            StubStrategy('fallback', RemediationOutcome(True, 'system', ''), calls),
        )).run(issue)

    assert calls == []
    issue = manager.get_issue(issue.id)
    assert issue.state == IssueState.UNRESOLVED
    assert issue.auto_remediation_attempts == []


@pytest.mark.parametrize('preview', [False, True])
def test_pipeline_timeout_cancels_decoder_lock_wait(
        database: DBHandler,
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        preview: bool,
) -> None:
    """A busy decoder must yield to the timeout without releasing another worker's lock."""
    calls: list[str] = []
    manager = DataIssuesManager(database)
    issue = _make_issue(database)
    strategy = StubStrategy('busy', RemediationOutcome(False, 'system', ''), calls, timeout=0.02)
    decoder = ethereum_transaction_decoder
    decode = (
        partial(
            decoder.decode_transaction_without_persistence, transaction=Mock(), tx_receipt=Mock(),
        )
        if preview else partial(decoder.decode_transaction_hashes, ignore_cache=True, tx_hashes=[])
    )
    pipeline = RemediationPipeline(manager, (
        strategy,
        StubStrategy('fallback', RemediationOutcome(True, 'system', ''), calls),
    ))
    with patch.object(strategy, 'attempt', side_effect=lambda issue: decode()):
        decoder.undecoded_tx_query_lock.acquire()
        task = Task(
            name='test remediation lock timeout', target=pipeline.run, args=(issue,),
        ).start()
        try:
            task.join(timeout=1)
            assert task.dead, 'Remediation kept waiting for the decoder lock after timeout'
            task.get()
            assert decoder.undecoded_tx_query_lock.acquire(blocking=False) is False
        finally:
            decoder.undecoded_tx_query_lock.release()
            task.join(timeout=5)

    assert calls == ['fallback']
    issue = manager.get_issue(issue.id)
    assert issue.state == IssueState.RESOLVED
    assert issue.auto_remediation_attempts[0]['attribution'] == 'timeout'
    assert decoder.undecoded_tx_query_lock.acquire(blocking=False)
    decoder.undecoded_tx_query_lock.release()
