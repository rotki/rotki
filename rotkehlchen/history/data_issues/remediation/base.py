import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import gevent

from rotkehlchen.history.data_issues.constants import IssueState
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.history.data_issues.manager import DataIssuesManager
    from rotkehlchen.history.data_issues.types import DataIssue

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DEFAULT_REMEDIATION_TIMEOUT: Final = 5


@dataclass(frozen=True)
class RemediationOutcome:
    resolved: bool
    attribution: str
    notes: str


class BaseRemediationStrategy(ABC):
    """Base interface for automatic data issue remediation strategies."""

    name: str
    timeout: int = DEFAULT_REMEDIATION_TIMEOUT

    @abstractmethod
    def applies_to(self, issue: 'DataIssue') -> bool:
        """Return whether this strategy can attempt to remediate the issue."""

    @abstractmethod
    def attempt(self, issue: 'DataIssue') -> RemediationOutcome:
        """Try to remediate the issue and return the outcome."""


class RemediationPipeline:
    """Run remediation strategies for a data issue in declared order."""

    def __init__(
            self,
            manager: 'DataIssuesManager',
            strategies: tuple[BaseRemediationStrategy, ...],
    ) -> None:
        self.manager = manager
        self.strategies = strategies

    def run(self, issue: 'DataIssue') -> None:
        if issue.state in {IssueState.RESOLVED, IssueState.DISMISSED}:
            return
        if issue.state in {IssueState.OPEN, IssueState.UNRESOLVED}:
            issue = self.manager.update_state(issue.id, IssueState.AUTO_REMEDIATING)

        if len(applicable_strategies := tuple(
            strategy for strategy in self.strategies if strategy.applies_to(issue)
        )) == 0:
            self.manager.update_state(issue.id, IssueState.UNRESOLVED)
            return

        for strategy in applicable_strategies:
            started_at = ts_now()
            try:
                with gevent.Timeout(strategy.timeout):
                    outcome = strategy.attempt(issue)
            except gevent.Timeout:
                outcome = RemediationOutcome(
                    resolved=False,
                    attribution='timeout',
                    notes=f'Strategy exceeded {strategy.timeout}s time budget',
                )

            attempt = {
                'strategy': strategy.name,
                'started_at': started_at,
                'finished_at': ts_now(),
                'resolved': outcome.resolved,
                'attribution': outcome.attribution,
                'notes': outcome.notes,
            }
            log.debug('Data issue remediation attempt: %s', attempt)
            self.manager.append_auto_remediation_attempt(issue.id, attempt)
            if outcome.resolved is True:
                self.manager.update_state(
                    issue.id,
                    IssueState.RESOLVED,
                    resolution={
                        'auto': True,
                        'strategy': strategy.name,
                        'attribution': outcome.attribution,
                        'notes': outcome.notes,
                    },
                )
                return

            gevent.sleep(0)

        self.manager.update_state(issue.id, IssueState.UNRESOLVED)
