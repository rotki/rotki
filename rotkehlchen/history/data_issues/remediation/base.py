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
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.data_issues.constants import IssueState
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.history.data_issues.manager import DataIssuesManager
    from rotkehlchen.history.data_issues.types import DataIssue

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DEFAULT_REMEDIATION_TIMEOUT: Final = 30


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
    """

    name: str
    timeout: float = DEFAULT_REMEDIATION_TIMEOUT

    @abstractmethod
    def applies_to(self, issue: DataIssue) -> bool:
        """Return whether this strategy can attempt to remediate the issue."""

    @abstractmethod
    def attempt(self, issue: DataIssue) -> RemediationOutcome:
        """Try to remediate the issue and return the outcome."""


class RemediationPipeline:
    """Run remediation strategies for a data issue in declared order."""

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
        """Cancel on budget expiry and join before allowing another strategy to mutate data.

        Cancellation finishes at the next checkpoint, so in-flight blocking I/O can
        extend elapsed time beyond the budget. Never abandon a mutating worker.
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
            task.join()
            raise

        if task.dead is False:
            task.request_cancellation(f'Strategy exceeded {strategy.timeout}s time budget')
            task.join()
            return RemediationOutcome(
                resolved=False,
                attribution='timeout',
                notes=f'Strategy exceeded {strategy.timeout}s time budget',
            )

        return result_of(task)

    def run(self, issue: DataIssue) -> None:
        if issue.state in {IssueState.RESOLVED, IssueState.DISMISSED}:
            return
        strategies = tuple(strategy for strategy in self.strategies if strategy.applies_to(issue))
        if len(strategies) == 0:
            # TODO: Persist the exhausted/no-applicable outcome instead of leaving the issue open.
            return
        if issue.state in {IssueState.OPEN, IssueState.UNRESOLVED}:
            issue = self.manager.update_state(issue.id, IssueState.AUTO_REMEDIATING)

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
                    attempt['resolved'] = outcome.resolved
                    attempt['success'] = outcome.resolved
                    if outcome.notes != '':
                        attempt['notes'] = outcome.notes
                        attempt['reason'] = outcome.notes
                if outcome.record_attempt:
                    log.debug('Data issue remediation attempt: %s', attempt)
                    self.manager.append_auto_remediation_attempt(issue.id, attempt)
                if outcome.resolved:
                    self.manager.update_state(
                        issue_id=issue.id,
                        state=IssueState.RESOLVED,
                        resolution={
                            'attribution': outcome.attribution,
                            'notes': outcome.notes,
                            'strategy': strategy.name,
                        },
                    )
                    return

                sleep(0)
        finally:
            if self.manager.get_issue(issue.id).state == IssueState.AUTO_REMEDIATING:
                self.manager.update_state(issue.id, IssueState.UNRESOLVED)
