from enum import StrEnum
from typing import Final


class IssueKind(StrEnum):
    CURRENT_BALANCE_MISMATCH = 'current_balance_mismatch'
    NEGATIVE_BALANCE = 'negative_balance'
    TRACKED_ADDRESS_TRANSFER = 'tracked_address_transfer'
    REBASING_TOKEN = 'rebasing_token'
    UNMATCHED_BRIDGE = 'unmatched_bridge'


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
    IssueKind.TRACKED_ADDRESS_TRANSFER: IssueSeverity.WARNING,
    IssueKind.REBASING_TOKEN: IssueSeverity.WARNING,
    IssueKind.UNMATCHED_BRIDGE: IssueSeverity.WARNING,
}

ALLOWED_STATE_TRANSITIONS: Final[dict[IssueState, frozenset[IssueState]]] = {
    IssueState.OPEN: frozenset({
        IssueState.AUTO_REMEDIATING,
        IssueState.RESOLVED,
        IssueState.DISMISSED,
    }),
    IssueState.AUTO_REMEDIATING: frozenset({
        IssueState.OPEN,  # a remediation run that attempted nothing hands the issue back
        IssueState.RESOLVED,
        IssueState.UNRESOLVED,
        IssueState.DISMISSED,
    }),
    IssueState.UNRESOLVED: frozenset({
        IssueState.AUTO_REMEDIATING,
        IssueState.OPEN,
        IssueState.RESOLVED,
        IssueState.DISMISSED,
    }),
    IssueState.RESOLVED: frozenset({IssueState.OPEN, IssueState.DISMISSED}),
    IssueState.DISMISSED: frozenset(),
}


def transition_sources(target: IssueState) -> tuple[IssueState, ...]:
    """The states from which ALLOWED_STATE_TRANSITIONS permits moving to `target`.

    Bulk updates filter their rows with this instead of hand-writing a state exclusion,
    so they can never reach a transition that the table forbids.
    """
    return tuple(
        source for source, targets in ALLOWED_STATE_TRANSITIONS.items() if target in targets
    )
