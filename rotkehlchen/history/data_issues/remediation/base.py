from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from time import monotonic, sleep
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.concurrency import (
    CancellationToken,
    Task,
    TaskCancelledError,
    checkpoint,
    result_of,
)
from rotkehlchen.errors.misc import InputError, NotFoundError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.data_issues.constants import IssueState
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.history.data_issues.manager import DataIssuesManager
    from rotkehlchen.history.data_issues.types import DataIssue

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DEFAULT_REMEDIATION_TIMEOUT: Final = 30
CANCELLATION_GRACE_PERIOD: Final = 10


class RemediationWorkerStuckError(RuntimeError):
    """A cancelled remediation worker is still running after the cancellation grace period."""


class _IssueChangedError(Exception):
    """The issue was dismissed or deleted by someone else while the pipeline worked on it."""


def _write[**P](
        method: Callable[P, DataIssue],
        *args: P.args,
        **kwargs: P.kwargs,
) -> DataIssue:
    """Call a manager write, reporting a rejected one as `_IssueChangedError`.

    The manager raises `InputError` for a transition the current state does not allow, or
    for an issue that left the state the pipeline expects, and `NotFoundError` for a
    missing row. Both mean the issue changed underneath the pipeline,
    which must skip that issue rather than abort the whole run.
    """
    try:
        return method(*args, **kwargs)
    except (InputError, NotFoundError) as e:
        raise _IssueChangedError(str(e)) from e


@dataclass(frozen=True)
class RemediationOutcome:
    resolved: bool
    attribution: str
    notes: str
    attempt_data: dict[str, Any] = field(default_factory=dict)
    record_attempt: bool = True


class BaseRemediationStrategy(ABC):
    """Interface for automatic data issue remediation strategies.

    The timeout is a cooperative budget: attempts must use cancellation-aware waits
    and checkpoints between units of work. Blocking I/O must have its own timeout.
    A worker that does not stop within CANCELLATION_GRACE_PERIOD of its cancellation
    is abandoned with a logged error and the whole remediation run aborts.
    """

    name: str
    timeout: float = DEFAULT_REMEDIATION_TIMEOUT

    @abstractmethod
    def applies_to(self, issue: DataIssue) -> bool:
        """Return whether this strategy can attempt to remediate the issue.

        Runs outside the time budget and cannot be cancelled, so it must decide from
        the issue's own fields only: no database or network access. Anything that needs
        loading belongs in `attempt`, which reports an issue it turns out to have nothing
        to do for as `not_applicable`.
        """

    @abstractmethod
    def attempt(self, issue: DataIssue) -> RemediationOutcome:
        """Try to remediate the issue within the time budget and return the outcome."""


def _join_after_cancellation(task: Task, strategy: BaseRemediationStrategy) -> None:
    """Wait for a cancelled worker for at most CANCELLATION_GRACE_PERIOD, then give up loudly.

    Cancellation is cooperative, so a worker blocked in network or database I/O never
    reaches a checkpoint and may outlive its budget. Waiting on it must still be bounded:
    otherwise one hung strategy freezes the remediation run and every later scheduled one.

    Deliberately never calls checkpoint(): control must not return to the caller, and so
    to another strategy, while this worker may still be committing.
    """
    cancellation_requested_at = monotonic()
    deadline = cancellation_requested_at + CANCELLATION_GRACE_PERIOD
    while task.dead is False and (remaining := deadline - monotonic()) > 0:
        task.join(min(remaining, 0.1))

    if task.dead is False:
        elapsed = monotonic() - cancellation_requested_at
        log.error(
            'Remediation strategy %s is still running %.1fs after cancellation, past the '
            '%ss grace period. Abandoning it; the remediation run cannot continue.',
            strategy.name,
            elapsed,
            CANCELLATION_GRACE_PERIOD,
        )
        raise RemediationWorkerStuckError(
            f'Remediation strategy {strategy.name} did not stop within '
            f'{CANCELLATION_GRACE_PERIOD}s of its cancellation',
        )


class RemediationPipeline:
    """Run remediation strategies for a data issue in declared order.

    Each strategy gets a cooperative time budget plus a bounded cancellation grace period.
    A worker that still runs after that grace is logged as an error and abandoned by
    raising `RemediationWorkerStuckError`, which aborts the run.
    """

    def __init__(
            self,
            manager: DataIssuesManager,
            strategies: tuple[BaseRemediationStrategy, ...],
    ) -> None:
        self.manager = manager
        self.strategies = strategies

    def _attempt_with_budget(
            self,
            strategy: BaseRemediationStrategy,
            issue: DataIssue,
    ) -> RemediationOutcome:
        """Run the strategy under its time budget, cancelling it when it expires.

        Cancellation is cooperative and only lands at the worker's next checkpoint, so
        in-flight blocking I/O can outlive the budget. The worker is then awaited for a
        bounded grace period and, if it is still alive, `RemediationWorkerStuckError` is
        raised instead of waiting forever. A mutating worker is therefore never abandoned
        silently, and no other strategy starts while one may still be committing.
        """
        token = CancellationToken()
        task = Task(
            name=f'data issue remediation: {strategy.name}',
            target=strategy.attempt,
            args=(issue,),
            token=token,
        ).start()
        deadline = monotonic() + strategy.timeout
        try:
            while task.dead is False and (remaining := deadline - monotonic()) > 0:
                task.join(min(remaining, 0.1))
                checkpoint()
        except TaskCancelledError:
            task.request_cancellation('Data issue remediation was cancelled')
            _join_after_cancellation(task, strategy)
            raise

        if task.dead is False:
            task.request_cancellation(f'Strategy exceeded {strategy.timeout}s time budget')
            _join_after_cancellation(task, strategy)
            if not isinstance(task.exception, TaskCancelledError):
                return result_of(task)
            return RemediationOutcome(
                resolved=False,
                attribution='timeout',
                notes=f'Strategy exceeded {strategy.timeout}s time budget',
            )

        return result_of(task)

    def run(self, issue: DataIssue) -> None:
        """Try the applicable strategies in order until one resolves the issue.

        A resolving attempt and the `RESOLVED` state are written in one update. Otherwise
        a crash between the two would leave a successful final attempt on an unresolved
        issue, which is never retried.

        An issue for which no strategy recorded an attempt returns to the state it had
        before the run, so it is picked up again by the next one.

        An issue the user dismisses or deletes while a strategy works on it is skipped:
        the write it rejects is logged and the run continues with the next issue.
        """
        if issue.state in {IssueState.RESOLVED, IssueState.DISMISSED}:
            return
        strategies = tuple(strategy for strategy in self.strategies if strategy.applies_to(issue))
        if len(strategies) == 0:
            return
        try:
            self._run_strategies(issue, strategies)
        except _IssueChangedError as e:
            log.warning(
                'Data issue %s changed during its remediation, skipping it: %s', issue.id, e,
            )

    def _run_strategies(
            self,
            issue: DataIssue,
            strategies: tuple[BaseRemediationStrategy, ...],
    ) -> None:
        state_before_run = IssueState(issue.state)
        if state_before_run in {IssueState.OPEN, IssueState.UNRESOLVED}:
            issue = _write(
                self.manager.update_state,
                issue_id=issue.id,
                state=IssueState.AUTO_REMEDIATING,
                expected_state=state_before_run,
            )

        attempt_recorded, retryable, resolved = False, False, False
        try:
            for strategy in strategies:
                try:
                    outcome = self._attempt_with_budget(strategy, issue)
                except (RemoteError, DeserializationError, InputError) as e:
                    log.exception(
                        'Remediation strategy %s failed for issue %s', strategy.name, issue.id,
                    )
                    outcome = RemediationOutcome(
                        resolved=False,
                        attribution='strategy_failed',
                        notes=str(e),
                    )

                attempt = {
                    'attribution': outcome.attribution,
                    'strategy': strategy.name,
                    'timestamp': ts_now(),
                    **outcome.attempt_data,
                }
                if len(outcome.attempt_data) == 0:
                    attempt['success'] = outcome.resolved
                    if outcome.notes != '':
                        attempt['reason'] = outcome.notes
                if outcome.resolved:
                    log.debug('Data issue remediation attempt: %s', attempt)
                    _write(
                        self.manager.update_state,
                        issue_id=issue.id,
                        state=IssueState.RESOLVED,
                        attempt=attempt if outcome.record_attempt else None,
                        resolution={
                            'attribution': outcome.attribution,
                            'notes': outcome.notes,
                            'strategy': strategy.name,
                        },
                        expected_state=IssueState.AUTO_REMEDIATING,
                    )
                    resolved = True
                    return
                if outcome.record_attempt:
                    log.debug('Data issue remediation attempt: %s', attempt)
                    if _write(
                        self.manager.append_auto_remediation_attempt, issue.id, attempt,
                    ).state != IssueState.AUTO_REMEDIATING:
                        raise _IssueChangedError('it left the auto-remediating state')
                    attempt_recorded = True

                sleep(0)
            retryable = attempt_recorded is False
        except (TaskCancelledError, RemediationWorkerStuckError):
            # Neither case records an attempt, so the issue must stay retryable.
            retryable = attempt_recorded is False
            raise
        finally:
            if resolved is False:
                self._leave_auto_remediating(
                    issue_id=issue.id,
                    state=(
                        state_before_run
                        if retryable and state_before_run == IssueState.OPEN
                        else IssueState.UNRESOLVED
                    ),
                )

    def _leave_auto_remediating(self, issue_id: int, state: IssueState) -> None:
        """Move an issue the run left in `AUTO_REMEDIATING` to `state`.

        Runs while the pipeline unwinds, so it never raises for an issue that left that
        state or was deleted meanwhile: that would replace the exception already propagating.
        """
        try:
            self.manager.update_state(
                issue_id=issue_id,
                state=state,
                expected_state=IssueState.AUTO_REMEDIATING,
            )
        except (InputError, NotFoundError) as e:
            log.warning(
                'Data issue %s changed during its remediation, leaving its state as is: %s',
                issue_id,
                e,
            )
