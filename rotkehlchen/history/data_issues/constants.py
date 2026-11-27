from enum import StrEnum
from typing import Final


class IssueKind(StrEnum):
    CURRENT_BALANCE_MISMATCH = 'current_balance_mismatch'
    INCOMPLETE_SWAP = 'incomplete_swap'
    INVALID_EVENT_AMOUNT = 'invalid_event_amount'
    MISSING_COST_BASIS = 'missing_cost_basis'
    MISSING_PRICE = 'missing_price'
    NEGATIVE_BALANCE = 'negative_balance'
    REBASING_TOKEN = 'rebasing_token'
    UNMATCHED_BRIDGE = 'unmatched_bridge'
    UNMATCHED_EXCHANGE_TRANSFER = 'unmatched_exchange_transfer'


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
    IssueKind.INCOMPLETE_SWAP: IssueSeverity.WARNING,
    IssueKind.INVALID_EVENT_AMOUNT: IssueSeverity.WARNING,
    IssueKind.MISSING_COST_BASIS: IssueSeverity.WARNING,
    IssueKind.MISSING_PRICE: IssueSeverity.WARNING,
    IssueKind.NEGATIVE_BALANCE: IssueSeverity.WARNING,
    IssueKind.REBASING_TOKEN: IssueSeverity.WARNING,
    IssueKind.UNMATCHED_BRIDGE: IssueSeverity.WARNING,
    IssueKind.UNMATCHED_EXCHANGE_TRANSFER: IssueSeverity.WARNING,
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
