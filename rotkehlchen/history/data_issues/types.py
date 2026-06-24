from dataclasses import dataclass
from typing import Any, NotRequired, TypeAlias, TypedDict


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


DataIssuePayload: TypeAlias = NegativeBalanceIssuePayload | CurrentBalanceMismatchIssuePayload
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
