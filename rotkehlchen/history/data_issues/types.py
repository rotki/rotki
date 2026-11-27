from dataclasses import dataclass
from typing import Any, Literal, NotRequired, TypedDict

type RebasingQueryFailure = Literal[
    'archive_node_unavailable',
    'historical_balance_query_failed',
    'missing_transaction',
    'unsupported_bucket',
]

type RedecodeComparisonResult = Literal[
    'redecoding_failed',
    'redecoding_would_change_balance',
    'redecoding_would_not_change_balance',
]


class BaseIssuePayload(TypedDict):
    """Common optional payload fields shared by all data issue kinds."""
    resolution: NotRequired[dict[str, Any]]


class TransactionDecodingComparison(TypedDict):
    tx_hash: str
    group_identifier: str
    saved_events: list[dict[str, Any]]
    decoded_events: list[dict[str, Any]]


class AutoRemediationAttempt(TypedDict):
    attribution: str
    strategy: str
    success: NotRequired[bool]
    timestamp: int
    reason: NotRequired[str]
    result: NotRequired[RedecodeComparisonResult]
    customized_transaction_count: NotRequired[int]
    changed_transaction_count: NotRequired[int]
    transactions: NotRequired[list[TransactionDecodingComparison]]
    amount_tolerance: NotRequired[str]
    time_range: NotRequired[int]
    movement_ids: NotRequired[list[int]]
    window_fingerprint: NotRequired[str]
    matched_movement_ids: NotRequired[list[int]]


class EventIssuePayload(BaseIssuePayload):
    """Common payload fields for event-scoped data issues."""
    event_identifier: int


class InvalidEventAmountIssuePayload(EventIssuePayload):
    """Payload for an event-scoped issue where an event has an invalid (negative) amount."""
    amount: str


class NegativeBalanceIssuePayload(EventIssuePayload):
    """Payload for an event-scoped issue where derived balance goes below zero."""
    in_memory_negative_amount: str
    derived_balance_before_event: str
    reason: NotRequired[Literal['untracked_exchange']]


class CurrentBalanceMismatchIssuePayload(BaseIssuePayload):
    """Payload for a bucket-scoped issue comparing derived and live chain balances."""
    derived_balance: str
    observed_balance: str
    delta: str
    queried_at_ts: int
    latest_event_identifier: int | None


class RebasingTokenIssuePayload(EventIssuePayload):
    """Payload for a rebasing balance that could not be verified on-chain."""
    block_number: int | None
    reason: RebasingQueryFailure


class UnmatchedBridgeIssuePayload(EventIssuePayload):
    """Payload for an event-scoped issue about a bridge leg with no matched counterpart.

    direction is 'deposit' for a source-chain outflow whose destination leg is unknown
    past the bridge's expected settlement window, and 'withdrawal' for a destination
    chain inflow whose source leg is unknown.
    """
    group_identifier: str
    direction: str
    counterparty: NotRequired[str]
    bridge: NotRequired[dict[str, Any]]


type MissingPriceDirection = Literal['receive', 'spend', 'fee', 'swap']
type IncompleteSwapReason = Literal['ignored_asset', 'ignored_action', 'missing_counterpart_leg']
type ExchangeTransferSubtype = Literal['spend', 'receive']


class MissingPriceIssuePayload(EventIssuePayload):
    """Payload for a priced cost-basis event whose asset lacked a historical price."""
    group_identifier: str
    to_asset: str
    amount: str
    direction: MissingPriceDirection


class MissingCostBasisIssuePayload(EventIssuePayload):
    """Payload for a spend or transfer whose quantity exceeded available lots."""
    group_identifier: str
    requested_amount: str
    covered_amount: str
    uncovered_amount: str
    fallback_basis: Literal['0']


class SwapLegSummary(TypedDict):
    """Compact factual summary of one leg present in an incomplete swap group."""
    event_identifier: int
    subtype: str
    asset: str
    amount: str


class IncompleteSwapIssuePayload(EventIssuePayload):
    """Payload for a swap group missing a valid counterpart leg or containing an excluded leg."""
    group_identifier: str
    event_identifiers: list[int]
    present_legs: list[SwapLegSummary]
    missing_or_excluded_reason: IncompleteSwapReason
    excluded_assets: list[str]


class UnmatchedExchangeTransferIssuePayload(EventIssuePayload):
    """Payload for an exchange transfer movement with no matched counterpart link."""
    group_identifier: str
    subtype: ExchangeTransferSubtype
    amount: str
    tx_ref: NotRequired[str]
    address: NotRequired[str]


class SuggestedAction(TypedDict):
    """Machine-readable remediation action surfaced alongside a data issue."""
    action: str
    params: dict[str, Any]
    endpoint: str
    requires_input: list[str]


type DataIssuePayload = (
    InvalidEventAmountIssuePayload |
    NegativeBalanceIssuePayload |
    CurrentBalanceMismatchIssuePayload |
    RebasingTokenIssuePayload |
    UnmatchedBridgeIssuePayload |
    MissingPriceIssuePayload |
    MissingCostBasisIssuePayload |
    IncompleteSwapIssuePayload |
    UnmatchedExchangeTransferIssuePayload
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
    event_identifier: int | None = None


@dataclass(frozen=True)
class DataIssueFilters:
    """Optional filters for listing persisted data quality issues."""
    kind: str | None = None
    state: str | None = None
    location: str | None = None
    location_label: str | None = None
    protocol: str | None = None
    asset: str | None = None
