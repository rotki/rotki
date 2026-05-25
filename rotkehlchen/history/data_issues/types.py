from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DataIssue:
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
    kind: str | None = None
    state: str | None = None
    location: str | None = None
    location_label: str | None = None
    protocol: str | None = None
    asset: str | None = None
