from enum import StrEnum
from typing import Final


class IssueKind(StrEnum):
    CURRENT_BALANCE_MISMATCH = 'current_balance_mismatch'
    NEGATIVE_BALANCE = 'negative_balance'


class IssueState(StrEnum):
    OPEN = 'open'
    AUTO_REMEDIATING = 'auto_remediating'
    UNRESOLVED = 'unresolved'
    RESOLVED = 'resolved'
    DISMISSED = 'dismissed'


class IssueSeverity(StrEnum):
    WARNING = 'warning'


ISSUE_KIND_SEVERITY: Final[dict[IssueKind, IssueSeverity]] = {
    IssueKind.CURRENT_BALANCE_MISMATCH: IssueSeverity.WARNING,
    IssueKind.NEGATIVE_BALANCE: IssueSeverity.WARNING,
}

ALLOWED_STATE_TRANSITIONS: Final[dict[IssueState, frozenset[IssueState]]] = {
    IssueState.OPEN: frozenset({IssueState.AUTO_REMEDIATING}),
    IssueState.AUTO_REMEDIATING: frozenset({IssueState.RESOLVED, IssueState.UNRESOLVED}),
    IssueState.UNRESOLVED: frozenset({IssueState.AUTO_REMEDIATING}),
    IssueState.RESOLVED: frozenset(),
    IssueState.DISMISSED: frozenset(),
}
