from dataclasses import dataclass
from typing import Any, Literal, NotRequired, TypedDict


class BaseIssuePayload(TypedDict):
    """Common optional payload fields shared by all data issue kinds."""
    resolution: NotRequired[dict[str, Any]]


class NegativeBalanceIssuePayload(BaseIssuePayload):
    """Payload for an event-scoped issue where derived balance goes below zero."""
    event_identifier: int
    in_memory_negative_amount: str
    derived_balance_before_event: str


class CurrentBalanceMismatchIssuePayload(BaseIssuePayload):
    """Payload for a bucket-scoped issue comparing derived and live chain balances."""
    derived_balance: str
    observed_balance: str
    delta: str
    queried_at_ts: int
    latest_event_identifier: int | None


class RebasingTokenIssuePayload(BaseIssuePayload):
    """Payload for a rebasing balance that could not be verified on-chain."""
    event_identifier: int
    block_number: int | None
    reason: Literal[
        'archive_node_unavailable',
        'historical_balance_query_failed',
        'missing_transaction',
        'unsupported_bucket',
    ]


class UnmatchedBridgeIssuePayload(BaseIssuePayload):
    """Payload for an event-scoped issue about a bridge leg with no matched counterpart.

    direction is 'deposit' for a source-chain outflow whose destination leg is unknown
    past the bridge's expected settlement window, and 'withdrawal' for a destination
    chain inflow whose source leg is unknown.
    """
    event_identifier: int
    group_identifier: str
    direction: str
    counterparty: NotRequired[str]
    bridge: NotRequired[dict[str, Any]]


type DataIssuePayload = (
    NegativeBalanceIssuePayload |
    CurrentBalanceMismatchIssuePayload |
    RebasingTokenIssuePayload |
    UnmatchedBridgeIssuePayload
)
"""Typed payload variants accepted when writing data issues."""


@dataclass(frozen=True)
class DataIssue:
    """A persisted data quality issue shown in the issues inbox."""
    id: int
    kind: str
    location: str
    location_label: str
    protocol: str
    asset: str
    group_identifier: str | None
    ts_start: int
    ts_end: int
    severity: str
    state: str
    auto_remediation_attempts: list[Any]
    payload: dict[str, Any]
    created_at: int
    resolved_at: int | None


@dataclass(frozen=True)
class DataIssueFilters:
    """Optional filters for listing persisted data quality issues."""
    kind: str | None = None
    state: str | None = None
    location: str | None = None
    location_label: str | None = None
    protocol: str | None = None
    asset: str | None = None
