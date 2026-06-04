import json
import logging
from typing import TYPE_CHECKING, Any, cast

from rotkehlchen.errors.misc import InputError, NotFoundError
from rotkehlchen.history.data_issues.constants import (
    ALLOWED_STATE_TRANSITIONS,
    ISSUE_KIND_SEVERITY,
    IssueKind,
    IssueSeverity,
    IssueState,
)
from rotkehlchen.history.data_issues.types import (
    DataIssue,
    DataIssueFilters,
    DataIssuePayload,
    NegativeBalanceIssuePayload,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DATA_ISSUE_SELECT_COLUMNS = (
    'id, kind, location, location_label, protocol, asset, ts_start, ts_end, severity, state, '
    'auto_remediation_attempts_json, payload_json, created_at, resolved_at'
)

DATA_ISSUE_INSERT_QUERY = """
INSERT OR IGNORE INTO data_issues (
    kind,
    location,
    location_label,
    protocol,
    asset,
    event_identifier,
    ts_start,
    ts_end,
    severity,
    state,
    auto_remediation_attempts_json,
    payload_json,
    created_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def _row_to_data_issue(row: tuple[Any, ...]) -> DataIssue:
    return DataIssue(
        id=row[0],
        kind=row[1],
        location=row[2],
        location_label=row[3],
        protocol=row[4],
        asset=row[5],
        ts_start=row[6],
        ts_end=row[7],
        severity=row[8],
        state=row[9],
        auto_remediation_attempts=json.loads(row[10]),
        payload=json.loads(row[11]),
        created_at=row[12],
        resolved_at=row[13],
    )


def _validate_state_transition(current_state: str | IssueState, new_state: IssueState) -> None:
    if new_state == IssueState.DISMISSED:
        return

    if isinstance(current_state, IssueState):
        current = current_state
    else:
        current = IssueState(current_state)
    allowed = ALLOWED_STATE_TRANSITIONS.get(current, frozenset())
    if new_state not in allowed:
        raise InputError(
            f'Invalid data issue state transition from {current_state} to {new_state}',
        )


class DataIssuesManager:
    """Read and write data quality issues for the issues inbox."""

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    def write_issue(
            self,
            kind: IssueKind,
            location: str,
            location_label: str | None,
            protocol: str | None,
            asset: str | None,
            payload: DataIssuePayload,
            ts_start: int,
            ts_end: int,
            severity: IssueSeverity | None = None,
    ) -> int:
        """Write an issue row idempotently and return its id."""
        location_label = '' if location_label is None else location_label
        protocol = '' if protocol is None else protocol
        asset = '' if asset is None else asset
        issue_severity = severity if severity is not None else ISSUE_KIND_SEVERITY[kind]
        payload_json = json.dumps(payload, separators=(',', ':'))
        created_at = ts_now()
        if kind == IssueKind.NEGATIVE_BALANCE:
            event_identifier = cast('NegativeBalanceIssuePayload', payload)['event_identifier']
        else:  # kind == IssueKind.CURRENT_BALANCE_MISMATCH
            event_identifier = None
        with self.db.user_write() as write_cursor:
            write_cursor.execute(
                DATA_ISSUE_INSERT_QUERY,
                (
                    kind,
                    location,
                    location_label,
                    protocol,
                    asset,
                    event_identifier,
                    ts_start,
                    ts_end,
                    issue_severity,
                    IssueState.OPEN,
                    '[]',
                    payload_json,
                    created_at,
                ),
            )
            if write_cursor.rowcount == 1:
                return write_cursor.lastrowid

        issue_id, existing_state = self._get_issue_id_and_state_by_natural_key(
            kind=kind,
            location=location,
            location_label=location_label,
            protocol=protocol,
            asset=asset,
            event_identifier=event_identifier,
        )
        if existing_state == IssueState.DISMISSED:
            return issue_id

        with self.db.user_write() as write_cursor:
            if existing_state == IssueState.RESOLVED:
                write_cursor.execute(
                    'UPDATE data_issues SET state = ?, ts_start = ?, ts_end = ?, '
                    'payload_json = ?, resolved_at = NULL WHERE id = ?',
                    (IssueState.OPEN, ts_start, ts_end, payload_json, issue_id),
                )
            else:
                write_cursor.execute(
                    'UPDATE data_issues SET ts_start = ?, ts_end = ?, payload_json = ? '
                    'WHERE id = ?',
                    (ts_start, ts_end, payload_json, issue_id),
                )
        return issue_id

    def list_issues(self, filters: DataIssueFilters | None = None) -> list[DataIssue]:
        query = f'SELECT {DATA_ISSUE_SELECT_COLUMNS} FROM data_issues'
        where_parts: list[str] = []
        bindings: list[Any] = []
        if filters is not None:
            for column, value in (
                ('kind', filters.kind),
                ('state', filters.state),
                ('location', filters.location),
                ('location_label', filters.location_label),
                ('protocol', filters.protocol),
                ('asset', filters.asset),
            ):
                if value is not None:
                    where_parts.append(f'{column} = ?')
                    bindings.append(value)

        if len(where_parts) != 0:
            query += ' WHERE ' + ' AND '.join(where_parts)
        query += ' ORDER BY ts_start DESC, id DESC'

        with self.db.conn.read_ctx() as cursor:
            cursor.execute(query, bindings)
            return [_row_to_data_issue(row) for row in cursor]

    def get_issue(self, issue_id: int) -> DataIssue:
        with self.db.conn.read_ctx() as cursor:
            row = cursor.execute(
                f'SELECT {DATA_ISSUE_SELECT_COLUMNS} FROM data_issues WHERE id = ?',
                (issue_id,),
            ).fetchone()
        if row is None:
            raise NotFoundError(f'Data issue with id {issue_id} not found')
        return _row_to_data_issue(row)

    def update_state(
            self,
            issue_id: int,
            state: IssueState,
            attempt: dict[str, Any] | None = None,
            resolution: dict[str, Any] | None = None,
    ) -> DataIssue:
        _validate_state_transition((issue := self.get_issue(issue_id)).state, state)

        attempts = issue.auto_remediation_attempts
        if attempt is not None:
            attempts = [*attempts, attempt]

        payload = issue.payload
        if resolution is not None:
            payload = {**payload, 'resolution': resolution}

        resolved_at = issue.resolved_at
        if state == IssueState.RESOLVED:
            resolved_at = ts_now()
        elif state in {IssueState.OPEN, IssueState.AUTO_REMEDIATING, IssueState.UNRESOLVED}:
            resolved_at = None

        with self.db.user_write() as write_cursor:
            row = write_cursor.execute(
                'UPDATE data_issues SET state = ?, auto_remediation_attempts_json = ?, '
                'payload_json = ?, resolved_at = ? WHERE id = ? RETURNING '
                f'{DATA_ISSUE_SELECT_COLUMNS}',
                (
                    state,
                    json.dumps(attempts, separators=(',', ':')),
                    json.dumps(payload, separators=(',', ':')),
                    resolved_at,
                    issue_id,
                ),
            ).fetchone()
        if row is None:
            raise NotFoundError(f'Data issue with id {issue_id} not found')
        return _row_to_data_issue(row)

    def dismiss(self, issue_id: int) -> DataIssue:
        with self.db.user_write() as write_cursor:
            row = write_cursor.execute(
                'UPDATE data_issues SET state = ? WHERE id = ? RETURNING '
                f'{DATA_ISSUE_SELECT_COLUMNS}',
                (IssueState.DISMISSED, issue_id),
            ).fetchone()
        if row is None:
            raise NotFoundError(f'Data issue with id {issue_id} not found')
        return _row_to_data_issue(row)

    def resolve_manually(self, issue_id: int, note: str | None = None) -> DataIssue:
        issue = self.get_issue(issue_id)
        if issue.state == IssueState.DISMISSED:
            raise InputError('Cannot resolve a dismissed data issue')
        if issue.state == IssueState.RESOLVED:
            return issue

        payload = issue.payload
        resolution: dict[str, Any] = {'manual': True}
        if note is not None:
            resolution['note'] = note
        payload = {**payload, 'resolution': resolution}

        with self.db.user_write() as write_cursor:
            row = write_cursor.execute(
                'UPDATE data_issues SET state = ?, payload_json = ?, resolved_at = ? '
                f'WHERE id = ? RETURNING {DATA_ISSUE_SELECT_COLUMNS}',
                (
                    IssueState.RESOLVED,
                    json.dumps(payload, separators=(',', ':')),
                    ts_now(),
                    issue_id,
                ),
            ).fetchone()
        if row is None:
            raise NotFoundError(f'Data issue with id {issue_id} not found')
        return _row_to_data_issue(row)

    def _get_issue_id_and_state_by_natural_key(
            self,
            kind: str,
            location: str,
            location_label: str,
            protocol: str,
            asset: str,
            event_identifier: int | None,
    ) -> tuple[int, str]:
        if event_identifier is None:
            query = (
                'SELECT id, state FROM data_issues WHERE kind = ? AND location = ? AND '
                'location_label = ? AND protocol = ? AND asset = ? AND event_identifier IS NULL'
            )
            bindings: tuple[Any, ...] = (kind, location, location_label, protocol, asset)
        else:
            query = (
                'SELECT id, state FROM data_issues WHERE kind = ? AND location = ? AND '
                'location_label = ? AND protocol = ? AND asset = ? AND event_identifier = ?'
            )
            bindings = (kind, location, location_label, protocol, asset, event_identifier)

        with self.db.conn.read_ctx() as cursor:
            row = cursor.execute(query, bindings).fetchone()
        if row is None:
            raise NotFoundError('Expected existing data issue after upsert conflict')
        return row
