import json
import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, cast

from rotkehlchen.db.filtering import DataIssuesFilterQuery
from rotkehlchen.db.utils import get_query_chunks
from rotkehlchen.errors.misc import InputError, NotFoundError
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.constants import (
    ALLOWED_STATE_TRANSITIONS,
    ISSUE_KIND_SEVERITY,
    IssueKind,
    IssueSeverity,
    IssueState,
    transition_sources,
)
from rotkehlchen.history.data_issues.types import (
    AutoRemediationAttempt,
    CurrentBalanceMismatchIssuePayload,
    DataIssue,
    DataIssueFilters,
    DataIssuePayload,
    NegativeBalanceIssuePayload,
    RebasingTokenIssuePayload,
    TrackedAddressTransferIssuePayload,
    UnmatchedBridgeIssuePayload,
)
from rotkehlchen.history.events.structures.types import (
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import deserialize_evm_tx_hash
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DATA_ISSUE_COLUMN_NAMES = (
    'id',
    'kind',
    'location',
    'location_label',
    'protocol',
    'asset',
    'ts_start',
    'ts_end',
    'severity',
    'state',
    'auto_remediation_attempts_json',
    'payload_json',
    'created_at',
    'resolved_at',
)
DATA_ISSUE_COLUMNS = ', '.join(DATA_ISSUE_COLUMN_NAMES)
DATA_ISSUE_SELECT_QUERY = (
    f'SELECT {", ".join(f"data_issues.{column}" for column in DATA_ISSUE_COLUMN_NAMES)}, '
    'history_events.group_identifier FROM data_issues LEFT JOIN history_events ON '
    'data_issues.event_identifier = history_events.identifier'
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


def _row_to_data_issue(
        row: tuple[Any, ...],
        group_identifier: str | None = None,
) -> DataIssue:
    return DataIssue(
        id=row[0],
        kind=row[1],
        location=row[2],
        location_label=row[3],
        protocol=row[4],
        asset=row[5],
        group_identifier=row[14] if len(row) > 14 else group_identifier,
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
    if isinstance(current_state, IssueState):
        current = current_state
    else:
        current = IssueState(current_state)
    allowed = ALLOWED_STATE_TRANSITIONS.get(current, frozenset())
    if new_state not in allowed:
        raise InputError(
            f'Invalid data issue state transition from {current_state} to {new_state}',
        )


def _resolved_at_for(state: IssueState) -> int | None:
    """The `resolved_at` value a row takes when it enters `state`."""
    return ts_now() if state == IssueState.RESOLVED else None


def _source_states_clause(target: IssueState) -> tuple[str, list[IssueState]]:
    """SQL condition and bindings selecting the rows allowed to move to `target`."""
    sources = transition_sources(target)
    return f'state IN ({", ".join("?" * len(sources))})', list(sources)


def make_auto_remediation_attempt(
        success: bool,
        reason: str | None = None,
) -> AutoRemediationAttempt:
    attempt = AutoRemediationAttempt(
        attribution='system',
        strategy='historical_balance_reprocessing',
        success=success,
        timestamp=ts_now(),
    )
    if reason is not None:
        attempt['reason'] = reason
    return attempt


class DataIssuesManager:
    """Read and write data quality issues for the issues inbox."""

    def __init__(self, database: DBHandler) -> None:
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
        return self.write_issue_with_state(
            kind=kind,
            location=location,
            location_label=location_label,
            protocol=protocol,
            asset=asset,
            payload=payload,
            ts_start=ts_start,
            ts_end=ts_end,
            severity=severity,
        )[0]

    def write_issue_with_state(
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
    ) -> tuple[int, str | IssueState]:
        """Write an issue idempotently and return its id and resulting state.

        A dismissed issue is never revived. A resolved issue keeps a *manual* resolution
        when the rediscovered candidate is unchanged, while issues resolved automatically
        or by system cleanup reopen as soon as the candidate is seen again.
        """
        location_label = '' if location_label is None else location_label
        protocol = '' if protocol is None else protocol
        asset = '' if asset is None else asset
        issue_severity = severity if severity is not None else ISSUE_KIND_SEVERITY[kind]
        payload_json = json.dumps(payload, separators=(',', ':'))
        created_at = ts_now()
        if kind in (
            IssueKind.NEGATIVE_BALANCE,
            IssueKind.TRACKED_ADDRESS_TRANSFER,
            IssueKind.REBASING_TOKEN,
            IssueKind.UNMATCHED_BRIDGE,
        ):
            event_identifier = cast(
                'NegativeBalanceIssuePayload | TrackedAddressTransferIssuePayload | RebasingTokenIssuePayload | UnmatchedBridgeIssuePayload',  # noqa: E501
                payload,
            )['event_identifier']
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
                return write_cursor.lastrowid, IssueState.OPEN

        issue_id, existing_state = self._get_issue_id_and_state_by_natural_key(
            kind=kind,
            location=location,
            location_label=location_label,
            protocol=protocol,
            asset=asset,
            event_identifier=event_identifier,
        )
        if existing_state == IssueState.DISMISSED:
            return issue_id, existing_state

        if existing_state == IssueState.RESOLVED and self._keep_manual_resolution(
            issue_id=issue_id,
            ts_start=ts_start,
            ts_end=ts_end,
            payload=payload,
        ):
            return issue_id, existing_state

        with self.db.user_write() as write_cursor:
            if existing_state == IssueState.RESOLVED:
                _validate_state_transition(existing_state, IssueState.OPEN)
                write_cursor.execute(
                    'UPDATE data_issues SET state = ?, ts_start = ?, ts_end = ?, '
                    'payload_json = ?, resolved_at = ? WHERE id = ?',
                    (
                        IssueState.OPEN,
                        ts_start,
                        ts_end,
                        payload_json,
                        _resolved_at_for(IssueState.OPEN),
                        issue_id,
                    ),
                )
            else:
                write_cursor.execute(
                    'UPDATE data_issues SET ts_start = ?, ts_end = ?, payload_json = ? '
                    'WHERE id = ?',
                    (ts_start, ts_end, payload_json, issue_id),
                )
        resulting_state = (
            IssueState.OPEN if existing_state == IssueState.RESOLVED else existing_state
        )
        return issue_id, resulting_state

    def _keep_manual_resolution(
            self,
            issue_id: int,
            ts_start: int,
            ts_end: int,
            payload: DataIssuePayload,
    ) -> bool:
        """Whether a resolved issue keeps its manual resolution instead of reopening.

        Only a manual resolution is final: when a scan rediscovers the same unchanged
        candidate it must keep the user's decision and note. Issues resolved automatically
        or by system cleanup reopen as soon as the candidate is seen again, even when its
        content is unchanged. A manual decision is stored in the payload's ``resolution``
        entry with ``manual: true``; any other value means the user did not resolve it.
        """
        with self.db.conn.read_ctx() as cursor:
            row = cursor.execute(
                'SELECT ts_start, ts_end, payload_json FROM data_issues WHERE id = ?',
                (issue_id,),
            ).fetchone()
        if row is None:
            return False

        stored_ts_start, stored_ts_end, stored_payload_json = row
        stored_payload = dict(json.loads(stored_payload_json))
        resolution = stored_payload.get('resolution')
        if not isinstance(resolution, dict) or resolution.get('manual') is not True:
            return False

        stored_payload.pop('resolution')
        return (
            stored_ts_start == ts_start and
            stored_ts_end == ts_end and
            stored_payload == payload
        )

    def write_tracked_address_transfer_issues(
            self,
            candidates: Sequence[tuple[int, int, str, int, str, str, str, int]],
    ) -> None:
        """Write a batch of tracked-address-transfer candidates idempotently.

        Each candidate is ``(event_identifier, chain_id, tx_hash, sequence_index, location,
        location_label, asset, timestamp)``. Rows that already exist in exactly the state
        the candidate describes are left untouched, so a repeated scan of an unchanged
        history performs no writes to the issues table.
        """
        if len(candidates) == 0:
            return

        existing: dict[tuple[str, str, str, str, int], tuple[Any, ...]] = {}
        with self.db.conn.read_ctx() as cursor:
            for chunk, placeholders in get_query_chunks([row[0] for row in candidates]):
                for row in cursor.execute(
                    'SELECT id, location, location_label, protocol, asset, event_identifier, '
                    'state, ts_start, ts_end, payload_json FROM data_issues '
                    f'WHERE kind = ? AND event_identifier IN ({placeholders})',
                    [IssueKind.TRACKED_ADDRESS_TRANSFER, *chunk],
                ):
                    existing[row[1], row[2], row[3], row[4], row[5]] = row

        created_at = ts_now()
        inserts: list[tuple[Any, ...]] = []
        updates: list[tuple[Any, ...]] = []
        reopens: list[tuple[Any, ...]] = []
        for event_identifier, chain_id, tx_hash, sequence_index, location, label, asset, ts in candidates:  # noqa: E501
            payload = {
                'event_identifier': event_identifier,
                'chain_id': chain_id,
                'tx_hash': tx_hash,
                'sequence_index': sequence_index,
            }
            payload_json = json.dumps(payload, separators=(',', ':'))
            stored = existing.get((location, label, '', asset, event_identifier))
            if stored is None:
                inserts.append((
                    IssueKind.TRACKED_ADDRESS_TRANSFER,
                    location,
                    label,
                    '',
                    asset,
                    event_identifier,
                    ts,
                    ts,
                    ISSUE_KIND_SEVERITY[IssueKind.TRACKED_ADDRESS_TRANSFER],
                    IssueState.OPEN,
                    '[]',
                    payload_json,
                    created_at,
                ))
                continue

            issue_id, _, _, _, _, _, state, ts_start, ts_end, stored_json = stored
            if state == IssueState.DISMISSED:
                continue
            stored_payload = dict(json.loads(stored_json))
            resolution = stored_payload.pop('resolution', None)
            unchanged = ts_start == ts and ts_end == ts and stored_payload == payload
            if unchanged and (
                state != IssueState.RESOLVED or
                (isinstance(resolution, dict) and resolution.get('manual') is True)
            ):
                continue  # unchanged, and a manual resolution is final

            if state == IssueState.RESOLVED:
                _validate_state_transition(state, IssueState.OPEN)
                reopens.append((
                    IssueState.OPEN,
                    ts,
                    ts,
                    payload_json,
                    _resolved_at_for(IssueState.OPEN),
                    issue_id,
                ))
            else:
                updates.append((ts, ts, payload_json, issue_id))

        if len(inserts) == 0 and len(updates) == 0 and len(reopens) == 0:
            return  # an unchanged batch must not even open a write transaction

        with self.db.user_write() as write_cursor:
            if len(inserts) != 0:
                write_cursor.executemany(DATA_ISSUE_INSERT_QUERY, inserts)
            if len(updates) != 0:
                write_cursor.executemany(
                    'UPDATE data_issues SET ts_start = ?, ts_end = ?, payload_json = ? '
                    'WHERE id = ?',
                    updates,
                )
            if len(reopens) != 0:
                write_cursor.executemany(
                    'UPDATE data_issues SET state = ?, ts_start = ?, ts_end = ?, '
                    'payload_json = ?, resolved_at = ? WHERE id = ?',
                    reopens,
                )

    def repoint_tracked_address_transfer_issues(
            self,
            repoints: Mapping[int, int],
    ) -> None:
        """Point tracked-address-transfer issues at their replacement event rows.

        ``repoints`` maps issue id to the identifier of the event that replaced the one the
        issue was originally keyed by (same transaction and sequence index). A repoint that
        would collide with an issue already keyed by the replacement is not applied: the
        dangling duplicate is resolved by the system instead, so exactly one row keeps the
        natural key.
        """
        if len(repoints) == 0:
            return

        with self.db.user_write() as write_cursor:
            self._repoint_tracked_address_transfer_issues(
                write_cursor=write_cursor,
                repoints=repoints,
            )

    def _repoint_tracked_address_transfer_issues(
            self,
            write_cursor: DBCursor,
            repoints: Mapping[int, int],
    ) -> None:
        for issue_id, new_event_identifier in repoints.items():
            row = write_cursor.execute(
                'SELECT location, location_label, protocol, asset, state '
                'FROM data_issues WHERE id = ?',
                (issue_id,),
            ).fetchone()
            if row is None:
                continue
            location, label, protocol, asset, state = row
            if write_cursor.execute(
                'SELECT 1 FROM data_issues WHERE kind = ? AND location = ? '
                'AND location_label = ? AND protocol = ? AND asset = ? '
                'AND event_identifier = ? AND id != ?',
                (
                    IssueKind.TRACKED_ADDRESS_TRANSFER,
                    location,
                    label,
                    protocol,
                    asset,
                    new_event_identifier,
                    issue_id,
                ),
            ).fetchone() is not None:
                if state not in {IssueState.RESOLVED, IssueState.DISMISSED}:
                    write_cursor.execute(
                        'UPDATE data_issues SET state = ?, resolved_at = ?, '
                        "payload_json = json_set(payload_json, '$.resolution', json(?)) "
                        'WHERE id = ?',
                        (
                            IssueState.RESOLVED,
                            _resolved_at_for(IssueState.RESOLVED),
                            json.dumps({'reason': 'duplicate_of_replacement_event'}),
                            issue_id,
                        ),
                    )
                continue

            write_cursor.execute(
                "UPDATE data_issues SET event_identifier = ?, payload_json = "
                "json_set(payload_json, '$.event_identifier', ?) WHERE id = ?",
                (new_event_identifier, new_event_identifier, issue_id),
            )

    def reconcile_dangling_tracked_address_transfer_issues(self) -> None:
        """Reconcile tracked-address-transfer issues whose event row no longer exists.

        Forced redecoding deletes the original history event, which can also happen outside a
        remediation run (the user redecodes a transaction manually), so a stored
        ``event_identifier`` may dangle. Each dangling issue is matched to the event now
        occupying the same transaction and sequence index:

        - no such event and the transaction is gone, or the event is now a proper transfer:
          the issue is resolved by the system.
        - another event occupies the slot: the issue is repointed to it, so the next discovery
          does not create a duplicate for the replacement and the related-event link keeps
          working.
        """
        with self.db.conn.read_ctx() as cursor:
            dangling = cursor.execute(
                'SELECT data_issues.id, data_issues.location, data_issues.location_label, '
                'data_issues.protocol, data_issues.asset, data_issues.state, '
                'data_issues.payload_json FROM data_issues LEFT JOIN history_events '
                'ON data_issues.event_identifier = history_events.identifier '
                'WHERE data_issues.kind = ? AND data_issues.event_identifier IS NOT NULL '
                'AND history_events.identifier IS NULL',
                (IssueKind.TRACKED_ADDRESS_TRANSFER,),
            ).fetchall()

        dangling_by_transaction: defaultdict[tuple[int, str], list[tuple[Any, ...]]] = defaultdict(list)  # noqa: E501
        for issue_id, location, label, protocol, asset, state, payload_json in dangling:
            payload = json.loads(payload_json)
            if (
                isinstance(payload.get('chain_id'), int) is False or
                isinstance(payload.get('tx_hash'), str) is False or
                isinstance(payload.get('sequence_index'), int) is False
            ):
                continue  # written before the stable identity was stored, nothing to match

            dangling_by_transaction[payload['chain_id'], payload['tx_hash']].append((
                issue_id, location, label, protocol, asset, state, payload['sequence_index'],
            ))

        if len(dangling_by_transaction) == 0:
            return

        repoints: dict[int, int] = {}
        resolutions: list[tuple[int, str]] = []
        with self.db.conn.read_ctx() as cursor:
            for (chain_id, tx_hash), issues in dangling_by_transaction.items():
                location = issues[0][1]
                events_by_sequence = {
                    row[0]: row[1:]
                    for row in cursor.execute(
                        'SELECT history_events.sequence_index, history_events.identifier, '
                        'history_events.type, history_events.subtype '
                        'FROM history_events JOIN chain_events_info '
                        'ON chain_events_info.identifier = history_events.identifier '
                        'WHERE chain_events_info.tx_ref = ? AND history_events.location = ?',
                        (deserialize_evm_tx_hash(tx_hash), location),
                    )
                }
                transaction_exists = cursor.execute(
                    'SELECT 1 FROM evm_transactions WHERE tx_hash = ? AND chain_id = ?',
                    (deserialize_evm_tx_hash(tx_hash), chain_id),
                ).fetchone() is not None

                for issue_id, _, _, _, _, state, sequence_index in issues:
                    if state in {IssueState.RESOLVED, IssueState.DISMISSED}:
                        if (replacement := events_by_sequence.get(sequence_index)) is not None:
                            repoints[issue_id] = replacement[0]
                        continue  # a final issue only needs its link kept working

                    if transaction_exists is False:
                        resolutions.append((issue_id, json.dumps({
                            'reason': 'transaction_no_longer_exists',
                        })))
                        continue

                    if (replacement := events_by_sequence.get(sequence_index)) is None:
                        continue  # the event may still come back from a later redecode

                    repoints[issue_id] = replacement[0]
                    if (
                        replacement[1] == HistoryEventType.TRANSFER.serialize() and
                        replacement[2] == HistoryEventSubType.NONE.serialize()
                    ):
                        resolutions.append((issue_id, json.dumps({
                            'reason': 'replacement_event_is_proper_transfer',
                        })))

        if len(repoints) == 0 and len(resolutions) == 0:
            return

        resolved_at = _resolved_at_for(IssueState.RESOLVED)
        sources_clause, sources = _source_states_clause(IssueState.RESOLVED)
        with self.db.user_write() as write_cursor:
            self._repoint_tracked_address_transfer_issues(
                write_cursor=write_cursor,
                repoints=repoints,
            )
            for issue_id, resolution in resolutions:
                write_cursor.execute(
                    'UPDATE data_issues SET state = ?, resolved_at = ?, '
                    "payload_json = json_set(payload_json, '$.resolution', json(?)) "
                    f'WHERE id = ? AND {sources_clause}',
                    (
                        IssueState.RESOLVED,
                        resolved_at,
                        resolution,
                        issue_id,
                        *sources,
                    ),
                )

    def resolve_reprocessed_negative_balance_issues(self) -> None:
        """Resolve negative-balance issues whose bucket is no longer stopped.

        A negative-balance issue is written exactly when the pass records a stop for its
        bucket, so the issue no longer describes the derived balances only once the bucket
        has no stop at all. Reading the stops that the completed pass settled (they include
        the ones before its ``from_ts``, which block the bucket just the same) is exact for
        both scoped and full passes, unlike comparing the issue event with the events the
        pass happened to evaluate. Manually resolved and dismissed issues are never touched.
        """
        resolved_at = _resolved_at_for(IssueState.RESOLVED)
        sources_clause, sources = _source_states_clause(IssueState.RESOLVED)
        with self.db.user_write() as write_cursor:
            write_cursor.execute(
                'UPDATE data_issues SET state = ?, resolved_at = ?, '
                "payload_json = json_set(payload_json, '$.resolution', json(?)) "
                'WHERE kind = ? AND event_identifier IS NOT NULL AND NOT EXISTS ('
                'SELECT 1 FROM bucket_processing_stops s '
                'WHERE s.location = data_issues.location '
                'AND s.location_label = data_issues.location_label '
                'AND s.protocol = data_issues.protocol '
                'AND s.asset = data_issues.asset) AND '
                f'{sources_clause}',
                (
                    IssueState.RESOLVED,
                    resolved_at,
                    json.dumps({'reason': 'bucket_no_longer_blocked'}),
                    IssueKind.NEGATIVE_BALANCE,
                    *sources,
                ),
            )

    def resolve_superseded_negative_balance_issues(self, assets: frozenset[str]) -> None:
        """Resolve negative-balance issues for assets now handled as rebasing tokens."""
        if len(assets) == 0:
            return

        resolved_at = _resolved_at_for(IssueState.RESOLVED)
        sources_clause, sources = _source_states_clause(IssueState.RESOLVED)
        with self.db.user_write() as write_cursor:
            for chunk, placeholders in get_query_chunks(data=list(assets)):
                write_cursor.execute(
                    'UPDATE data_issues SET state = ?, resolved_at = ? WHERE kind = ? '
                    f'AND asset IN ({placeholders}) AND {sources_clause}',
                    [
                        IssueState.RESOLVED,
                        resolved_at,
                        IssueKind.NEGATIVE_BALANCE,
                        *chunk,
                        *sources,
                    ],
                )

    def report_current_balance_mismatch(
            self,
            location: str,
            location_label: str,
            asset: str,
            payload: CurrentBalanceMismatchIssuePayload,
            ts_start: int,
            ts_end: int,
    ) -> IssueState | str:
        """Write or refresh the mismatch issue of a wallet bucket and return its resulting state.

        An unresolved issue whose divergence grew is made open again for a new attempt, since the
        earlier attempt did not account for the larger difference. Dismissed issues are untouched.
        """
        previous_delta: FVal | None = None
        if len(existing := self.list_issues(DataIssueFilters(
            kind=IssueKind.CURRENT_BALANCE_MISMATCH,
            location=location,
            location_label=location_label,
            protocol='',
            asset=asset,
        ))) != 0 and existing[0].state == IssueState.UNRESOLVED:
            previous_delta = FVal(existing[0].payload['delta'])

        issue_id, state = self.write_issue_with_state(
            kind=IssueKind.CURRENT_BALANCE_MISMATCH,
            location=location,
            location_label=location_label,
            protocol=None,
            asset=asset,
            payload=payload,
            ts_start=ts_start,
            ts_end=ts_end,
        )
        if previous_delta is not None and abs(FVal(payload['delta'])) > abs(previous_delta):
            _validate_state_transition(state, IssueState.OPEN)
            with self.db.user_write() as write_cursor:
                write_cursor.execute(
                    'UPDATE data_issues SET state = ?, resolved_at = ? WHERE id = ? AND state = ?',
                    (IssueState.OPEN, _resolved_at_for(IssueState.OPEN), issue_id, state),
                )
            return IssueState.OPEN

        return state

    def resolve_current_balance_mismatch(
            self,
            location: str,
            location_label: str,
            asset: str,
    ) -> None:
        """Resolve, attributed to the system, a mismatch that is back within tolerance."""
        sources_clause, sources = _source_states_clause(IssueState.RESOLVED)
        with self.db.user_write() as write_cursor:
            write_cursor.execute(
                'UPDATE data_issues SET state = ?, resolved_at = ?, '
                "payload_json = json_set(payload_json, '$.resolution', json(?)) "
                "WHERE kind = ? AND location = ? AND location_label = ? AND protocol = '' "
                f'AND asset = ? AND {sources_clause}',
                (
                    IssueState.RESOLVED,
                    _resolved_at_for(IssueState.RESOLVED),
                    json.dumps({'reason': 'within_tolerance'}),
                    IssueKind.CURRENT_BALANCE_MISMATCH,
                    location,
                    location_label,
                    asset,
                    *sources,
                ),
            )

    def resolve_unmatched_bridge_issues_except(self, still_unmatched_ids: set[int]) -> None:
        """Resolve unmatched bridge issues whose event is no longer unmatched."""
        sources_clause, sources = _source_states_clause(IssueState.RESOLVED)
        query = (
            'UPDATE data_issues SET state = ?, resolved_at = ? WHERE kind = ? '
            f'AND {sources_clause}'
        )
        bindings: list[Any] = [
            IssueState.RESOLVED,
            _resolved_at_for(IssueState.RESOLVED),
            IssueKind.UNMATCHED_BRIDGE,
            *sources,
        ]
        if len(still_unmatched_ids) > 0:
            query += f' AND event_identifier NOT IN ({",".join("?" * len(still_unmatched_ids))})'
            bindings.extend(still_unmatched_ids)
        with self.db.user_write() as write_cursor:
            write_cursor.execute(query, bindings)

    def reset_orphaned_remediations(self) -> None:
        """Make remediation rows left by a previous process retryable after login."""
        _validate_state_transition(IssueState.AUTO_REMEDIATING, IssueState.UNRESOLVED)
        with self.db.user_write() as write_cursor:
            write_cursor.execute(
                'UPDATE data_issues SET state = ?, resolved_at = ? WHERE state = ?',
                (
                    IssueState.UNRESOLVED,
                    _resolved_at_for(IssueState.UNRESOLVED),
                    IssueState.AUTO_REMEDIATING,
                ),
            )

    def resolve_event_issues(
            self,
            kind: IssueKind,
            issues: list[tuple[str, str | None, str | None, str, int]],
    ) -> None:
        """Resolve event-scoped issues whose buckets processed successfully."""
        if len(issues) == 0:
            return

        resolved_at = _resolved_at_for(IssueState.RESOLVED)
        sources_clause, sources = _source_states_clause(IssueState.RESOLVED)
        with self.db.user_write() as write_cursor:
            write_cursor.executemany(
                'UPDATE data_issues SET state = ?, resolved_at = ? WHERE kind = ? '
                'AND location = ? AND location_label = ? AND protocol = ? AND asset = ? '
                f'AND event_identifier = ? AND {sources_clause}',
                [(
                    IssueState.RESOLVED,
                    resolved_at,
                    kind,
                    location,
                    location_label or '',
                    protocol or '',
                    asset,
                    event_identifier,
                    *sources,
                ) for location, location_label, protocol, asset, event_identifier in issues],
            )

    def list_issues(
            self,
            filters: DataIssueFilters | DataIssuesFilterQuery | None = None,
    ) -> list[DataIssue]:
        query = f'SELECT * FROM ({DATA_ISSUE_SELECT_QUERY})'
        where_parts: list[str] = []
        bindings: list[Any] = []
        if isinstance(filters, DataIssuesFilterQuery):
            filterstr, bindings = filters.prepare()
            query += f' {filterstr}'
        else:
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

    def count_issues(self, filter_query: DataIssuesFilterQuery) -> int:
        filterstr, bindings = filter_query.prepare(with_pagination=False, with_order=False)
        with self.db.conn.read_ctx() as cursor:
            return cursor.execute(
                f'SELECT COUNT(*) FROM data_issues {filterstr}',
                bindings,
            ).fetchone()[0]

    def get_issue(self, issue_id: int) -> DataIssue:
        with self.db.conn.read_ctx() as cursor:
            row = cursor.execute(
                f'SELECT * FROM ({DATA_ISSUE_SELECT_QUERY}) WHERE id = ?',
                (issue_id,),
            ).fetchone()
        if row is None:
            raise NotFoundError(f'Data issue with id {issue_id} not found')
        return _row_to_data_issue(row)

    def update_state(
            self,
            issue_id: int,
            state: IssueState,
            attempt: Mapping[str, Any] | None = None,
            resolution: dict[str, Any] | None = None,
    ) -> DataIssue:
        _validate_state_transition((issue := self.get_issue(issue_id)).state, state)

        attempts = issue.auto_remediation_attempts
        if attempt is not None:
            attempts = [
                *({key: value for key, value in old.items() if key != 'transactions'}
                  for old in attempts),
                attempt,
            ]

        payload = issue.payload
        if resolution is not None:
            payload = {**payload, 'resolution': resolution}

        with self.db.user_write() as write_cursor:
            row = write_cursor.execute(
                'UPDATE data_issues SET state = ?, auto_remediation_attempts_json = ?, '
                'payload_json = ?, resolved_at = ? WHERE id = ? RETURNING '
                f'{DATA_ISSUE_COLUMNS}',
                (
                    state,
                    json.dumps(attempts, separators=(',', ':')),
                    json.dumps(payload, separators=(',', ':')),
                    _resolved_at_for(state),
                    issue_id,
                ),
            ).fetchone()
        if row is None:
            raise NotFoundError(f'Data issue with id {issue_id} not found')
        return _row_to_data_issue(row, group_identifier=issue.group_identifier)

    def append_auto_remediation_attempt(
            self,
            issue_id: int,
            attempt: Mapping[str, Any],
            resolution: dict[str, Any] | None = None,
    ) -> DataIssue:
        issue = self.get_issue(issue_id)
        payload = (
            issue.payload if resolution is None else
            {**issue.payload, 'resolution': resolution}
        )
        with self.db.user_write() as write_cursor:
            row = write_cursor.execute(
                'UPDATE data_issues SET auto_remediation_attempts_json = ?, payload_json = ? '
                'WHERE id = ? '
                f'RETURNING {DATA_ISSUE_COLUMNS}',
                (
                    json.dumps([
                        *({key: value for key, value in old.items() if key != 'transactions'}
                          for old in issue.auto_remediation_attempts),
                        attempt,
                    ], separators=(',', ':')),
                    json.dumps(payload, separators=(',', ':')),
                    issue_id,
                ),
            ).fetchone()
        if row is None:
            raise NotFoundError(f'Data issue with id {issue_id} not found')
        return _row_to_data_issue(row, group_identifier=issue.group_identifier)

    def dismiss(self, issue_id: int) -> DataIssue:
        issue = self.get_issue(issue_id)
        if issue.state == IssueState.DISMISSED:
            return issue

        _validate_state_transition(issue.state, IssueState.DISMISSED)
        payload = dict(issue.payload)
        payload.pop('resolution', None)
        with self.db.user_write() as write_cursor:
            row = write_cursor.execute(
                'UPDATE data_issues SET state = ?, payload_json = ?, resolved_at = ? '
                f'WHERE id = ? RETURNING {DATA_ISSUE_COLUMNS}',
                (
                    IssueState.DISMISSED,
                    json.dumps(payload, separators=(',', ':')),
                    _resolved_at_for(IssueState.DISMISSED),
                    issue_id,
                ),
            ).fetchone()
        if row is None:
            raise NotFoundError(f'Data issue with id {issue_id} not found')
        return _row_to_data_issue(row, group_identifier=issue.group_identifier)

    def resolve_manually(self, issue_id: int, note: str | None = None) -> DataIssue:
        issue = self.get_issue(issue_id)
        if issue.state == IssueState.DISMISSED:
            raise InputError(
                f'Cannot resolve a dismissed data issue. Current state is {issue.state}',
            )
        if issue.state == IssueState.RESOLVED:
            raise InputError(
                f'Cannot resolve an already resolved data issue. Current state is {issue.state}',
            )

        payload = issue.payload
        resolution: dict[str, Any] = {'manual': True}
        if note is not None:
            resolution['note'] = note
        payload = {**payload, 'resolution': resolution}

        _validate_state_transition(issue.state, IssueState.RESOLVED)
        with self.db.user_write() as write_cursor:
            row = write_cursor.execute(
                'UPDATE data_issues SET state = ?, payload_json = ?, resolved_at = ? '
                f'WHERE id = ? RETURNING {DATA_ISSUE_COLUMNS}',
                (
                    IssueState.RESOLVED,
                    json.dumps(payload, separators=(',', ':')),
                    _resolved_at_for(IssueState.RESOLVED),
                    issue_id,
                ),
            ).fetchone()
        if row is None:
            raise NotFoundError(f'Data issue with id {issue_id} not found')
        return _row_to_data_issue(row, group_identifier=issue.group_identifier)

    def retry_auto_remediation(self, issue_id: int) -> tuple[DataIssue, bool]:
        issue = self.get_issue(issue_id)
        if issue.kind != IssueKind.REBASING_TOKEN:
            raise InputError(f'Auto-remediation is not supported for {issue.kind} data issues')
        if issue.state == IssueState.AUTO_REMEDIATING:
            return issue, False
        if issue.state not in {IssueState.OPEN, IssueState.UNRESOLVED}:
            raise InputError(
                f'Cannot retry auto-remediation for a {issue.state} data issue',
            )

        return self.update_state(issue_id, IssueState.AUTO_REMEDIATING), True

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
