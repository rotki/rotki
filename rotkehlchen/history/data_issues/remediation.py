"""Bounded, approved repairs of the history behind the historical balance engine.

A repair goes through three steps, each its own call:

1. preview: compute the exact proposed changes and their balance effects, without writing
   anything but the plan itself. The plan stores digests of the evidence it was computed from
   and expires after PLAN_TTL_SECONDS.
2. apply: refused unless the plan is pending, unexpired and its evidence unchanged. It applies
   only the plan's items, records an outcome per item, reprocesses the affected range and
   verifies the result. Applying twice is refused, so a retried request can't apply it again.
3. verify: re-read the affected buckets and issues and report whether the target was actually
   re-evaluated and repaired. Job completion and issue states are not evidence of repair: the
   bucket processing stops are.

Approval is not established here. The caller (the MCP server, through an elicitation the user
answers in their client) states how the plan was approved, and that statement is recorded in
the audit trail with every transition of the plan.

Two kinds of repair exist: redecoding transactions with the current decoders, and linking two
legs of one bridge transfer. Nothing else can be written through a plan: no SQL, no synthetic
opening balances, no tolerance changes and no issue dismissals.
"""
import copy
import hashlib
import json
import logging
import uuid
from collections import defaultdict
from enum import StrEnum
from operator import itemgetter
from typing import TYPE_CHECKING, Any, Final, cast

from rotkehlchen.constants import ZERO
from rotkehlchen.db.constants import HistoryEventLinkType, HistoryMappingState
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import InputError, NotFoundError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.data_issues.bucket_state import get_bucket_stops, make_bucket_key
from rotkehlchen.history.data_issues.constants import IssueState
from rotkehlchen.history.data_issues.diagnostics import (
    get_group_events,
    get_mapping_states,
    get_processing_state,
    make_bucket,
    serialize_bucket,
    serialize_effects,
    serialize_event_summary,
)
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import EventDirection
from rotkehlchen.locations.chains import EVM_LOCATIONS, location_to_chain_id
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_tx_hash
from rotkehlchen.tasks.bridges import (
    apply_bridge_match_to_events,
    classify_bridge_candidate,
    get_bridge_match_assets_in_collection,
    update_bridge_matched_event,
)
from rotkehlchen.tasks.data_issues import preview_transaction
from rotkehlchen.tasks.events import get_already_matched_event_ids
from rotkehlchen.tasks.historical_balances import Bucket, process_historical_balances
from rotkehlchen.types import EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, ChainID, TimestampMS
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

PLAN_TTL_SECONDS: Final = 30 * 60
MAX_PLAN_GROUPS: Final = 20
APPROVAL_METHODS: Final = frozenset({'mcp_elicitation'})


class PlanKind(StrEnum):
    REDECODE = 'redecode'
    BRIDGE_LINK = 'bridge_link'


class PlanState(StrEnum):
    PENDING = 'pending'
    APPLYING = 'applying'
    APPLIED = 'applied'
    PARTIALLY_APPLIED = 'partially_applied'
    FAILED = 'failed'
    REJECTED = 'rejected'
    EXPIRED = 'expired'
    STALE = 'stale'


class RemediationError(Exception):
    """A plan can't be created or applied. ``code`` names why, for the caller to act on."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _event_content(event: HistoryBaseEntry) -> dict[str, Any]:
    """What an event says, without its identity, so a saved and a decoded event compare."""
    return {
        'sequence_index': event.sequence_index,
        'event_type': event.event_type.serialize(),
        'event_subtype': event.event_subtype.serialize(),
        'asset': event.asset.identifier,
        'amount': str(event.amount),
        'location_label': event.location_label,
        'address': getattr(event, 'address', None),
        'counterparty': getattr(event, 'counterparty', None),
        'extra_data': event.extra_data,
    }


def _saved_digest(
        events: Sequence[HistoryBaseEntry],
        mapping_states: dict[int, list[HistoryMappingState]],
) -> str:
    """Digest of the saved events and their mapping states, to detect any later change."""
    return _digest(sorted(
        (
            event.identifier,
            _event_content(event),
            sorted(state.serialize() for state in mapping_states.get(event.identifier or -1, ())),
        ) for event in events
    ))


def _content_digest(events: Sequence[HistoryBaseEntry]) -> str:
    return _digest(sorted(
        (_event_content(event) for event in events),
        key=itemgetter('sequence_index', 'asset', 'amount'),
    ))


def _net_effects(events: Sequence[HistoryBaseEntry], treat_eth2_as_eth: bool) -> dict[Bucket, FVal]:  # noqa: E501
    net: dict[Bucket, FVal] = defaultdict(lambda: ZERO)
    for event in events:
        for bucket, direction in Bucket.from_event(event, treat_eth2_as_eth=treat_eth2_as_eth):
            net[bucket] += event.amount if direction == EventDirection.IN else -event.amount
    return net


def _effect_diff(
        before: Sequence[HistoryBaseEntry],
        after: Sequence[HistoryBaseEntry],
        treat_eth2_as_eth: bool,
) -> list[dict[str, Any]]:
    """The exact change of each bucket's net effect between two versions of the events."""
    before_net = _net_effects(before, treat_eth2_as_eth)
    after_net = _net_effects(after, treat_eth2_as_eth)
    return [{
        'bucket': serialize_bucket(bucket),
        'current_net': str(current := before_net.get(bucket, ZERO)),
        'proposed_net': str(proposed := after_net.get(bucket, ZERO)),
        'difference': str(proposed - current),
    } for bucket in sorted(
        {*before_net, *after_net},
        key=lambda x: (x.location, x.location_label or '', x.protocol or '', x.asset),
    ) if before_net.get(bucket, ZERO) != after_net.get(bucket, ZERO)]


def _event_diff(
        saved: Sequence[HistoryBaseEntry],
        decoded: Sequence[HistoryBaseEntry],
) -> dict[str, Any]:
    """Saved events the decoders would remove, decoded events they'd add, and changed ones.

    Events are paired by sequence index, which is how the decoders order a transaction.
    """
    saved_by_index = {event.sequence_index: event for event in saved}
    decoded_by_index = {event.sequence_index: event for event in decoded}
    changed = []
    for index in sorted(saved_by_index.keys() & decoded_by_index.keys()):
        saved_content = _event_content(saved_by_index[index])
        decoded_content = _event_content(decoded_by_index[index])
        if (fields := sorted(
            key for key in saved_content if saved_content[key] != decoded_content[key]
        )):
            changed.append({
                'sequence_index': index,
                'event_identifier': saved_by_index[index].identifier,
                'changed_fields': fields,
                'current': {key: saved_content[key] for key in fields if key != 'extra_data'},
                'proposed': {key: decoded_content[key] for key in fields if key != 'extra_data'},
            })
    return {
        'removed': [
            {'sequence_index': index, 'event_identifier': saved_by_index[index].identifier}
            for index in sorted(saved_by_index.keys() - decoded_by_index.keys())
        ],
        'added': [
            _event_content(decoded_by_index[index]) | {'extra_data': None}
            for index in sorted(decoded_by_index.keys() - saved_by_index.keys())
        ],
        'changed': changed,
    }


def _baseline(database: DBHandler, buckets: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """The stops and open issues of the affected buckets before the plan, for verification."""
    with database.conn.read_ctx() as cursor:
        stops = get_bucket_stops(cursor)
        issues = cursor.execute(
            'SELECT id, location, location_label, protocol, asset FROM data_issues '
            'WHERE state IN (?, ?, ?)',
            (IssueState.OPEN, IssueState.UNRESOLVED, IssueState.AUTO_REMEDIATING),
        ).fetchall()
    keys = {_bucket_key(bucket) for bucket in buckets}
    return {
        'stops': [{
            'bucket': bucket,
            'event_identifier': stop.event_identifier,
            'event_timestamp_ms': stop.event_timestamp,
        } for bucket in buckets if (stop := stops.get(_bucket_key(bucket))) is not None],
        'open_issue_ids': sorted(
            issue_id for issue_id, *key in issues
            if make_bucket_key(*key) in keys
        ),
    }


def _bucket_key(bucket: dict[str, Any]) -> tuple[str, str, str, str]:
    return make_bucket_key(
        location=bucket['location'],
        location_label=bucket['location_label'],
        protocol=bucket['protocol'],
        asset=bucket['asset'],
    )


def _save_plan(
        database: DBHandler,
        kind: PlanKind,
        plan: dict[str, Any],
        evidence_revision: str,
) -> dict[str, Any]:
    plan_id = uuid.uuid4().hex
    now = ts_now()
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT INTO remediation_plans(identifier, kind, state, created_at, expires_at, '
            'evidence_revision, plan) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (
                plan_id,
                kind.value,
                PlanState.PENDING.value,
                now,
                now + PLAN_TTL_SECONDS,
                evidence_revision,
                json.dumps(plan),
            ),
        )
        _audit(write_cursor, plan_id, 'created', {'kind': kind.value})
    return get_plan(database, plan_id)


def _audit(write_cursor: Any, plan_id: str, action: str, details: dict[str, Any]) -> None:
    write_cursor.execute(
        'INSERT INTO remediation_plan_audit(plan_identifier, timestamp, action, details) '
        'VALUES (?, ?, ?, ?)',
        (plan_id, ts_now(), action, json.dumps(details, default=str)),
    )


def get_plan(database: DBHandler, plan_id: str) -> dict[str, Any]:
    """The plan with its state and audit trail. May raise NotFoundError."""
    with database.conn.read_ctx() as cursor:
        if (row := cursor.execute(
            'SELECT identifier, kind, state, created_at, expires_at, evidence_revision, plan, '
            'result, applied_at FROM remediation_plans WHERE identifier = ?',
            (plan_id,),
        ).fetchone()) is None:
            raise NotFoundError(f'No remediation plan {plan_id}')
        audit = [{
            'timestamp_s': timestamp,
            'action': action,
            'details': json.loads(details),
        } for timestamp, action, details in cursor.execute(
            'SELECT timestamp, action, details FROM remediation_plan_audit '
            'WHERE plan_identifier = ? ORDER BY identifier',
            (plan_id,),
        )]

    state = row[2]
    if state == PlanState.PENDING and row[4] < ts_now():
        state = PlanState.EXPIRED.value  # expiry is evaluated on read, see apply_plan
    return {
        'plan_id': row[0],
        'kind': row[1],
        'state': state,
        'created_at_ts_s': row[3],
        'expires_at_ts_s': row[4],
        'evidence_revision': row[5],
        'plan': json.loads(row[6]),
        'result': None if row[7] is None else json.loads(row[7]),
        'applied_at_ts_s': row[8],
        'audit': audit,
    }


def preview_redecode(
        database: DBHandler,
        chains_aggregator: ChainsAggregator,
        group_identifiers: Sequence[str],
        replace_customized: bool,
) -> dict[str, Any]:
    """Preview redecoding the given EVM transactions with the current decoders.

    Works for ordinary events as well as customized ones: an ordinary transaction whose events
    lack metadata that today's decoders emit can be previewed without being marked customized
    first. A customized transaction is only included for replacement when replace_customized
    is set; otherwise its preview is still shown, as blocked.

    May raise RemediationError.
    """
    if not 0 < len(group_identifiers) <= MAX_PLAN_GROUPS:
        raise RemediationError(
            'invalid_scope',
            f'A plan covers between 1 and {MAX_PLAN_GROUPS} transactions',
        )

    treat_eth2_as_eth = CachedSettings().get_entry('treat_eth2_as_eth') is True
    items, affected, uncertainty = [], {}, []
    reloaded: set[ChainID] = set()
    for group_identifier in dict.fromkeys(group_identifiers):
        if len(saved := get_group_events(database, group_identifier)) == 0:
            raise RemediationError('unknown_group', 'A transaction of the plan has no events')
        if not isinstance(first := saved[0], EvmEvent) or first.location not in EVM_LOCATIONS:
            items.append({
                'group_identifier': group_identifier,
                'status': 'unsupported',
                'reason': 'Only EVM transactions can be redecoded through a plan',
            })
            continue

        chain_id = cast(
            'EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE',
            ChainID(location_to_chain_id(first.location)),
        )
        with database.conn.read_ctx() as cursor:
            mapping_states = get_mapping_states(cursor=cursor, events=saved)
        customized = any(HistoryMappingState.CUSTOMIZED in x for x in mapping_states.values())
        matched = any(HistoryMappingState.MATCHED in x for x in mapping_states.values())
        decoder = chains_aggregator.get_evm_manager(chain_id).transactions_decoder
        preview_exceptions: tuple[type[Exception], ...] = (
            RuntimeError,
            *decoder.possible_decoding_exceptions,
        )
        item: dict[str, Any] = {
            'group_identifier': group_identifier,
            'location': first.location,
            'chain_id': chain_id.serialize(),
            'tx_hash': str(first.tx_ref),
            'timestamp_ms': first.timestamp,
            'customized': customized,
            'replace_customized': customized and replace_customized,
            'has_matched_events': matched,
            'saved_digest': _saved_digest(saved, mapping_states),
        }
        try:
            decoded = preview_transaction(
                database=database,
                chains_aggregator=chains_aggregator,
                chain_id=chain_id,
                tx_hash=first.tx_ref,
                reload=chain_id not in reloaded,
            )
        except preview_exceptions as e:
            items.append(item | {'status': 'preview_failed', 'reason': str(e)})
            continue
        finally:
            reloaded.add(chain_id)

        diff = _effect_diff(saved, decoded, treat_eth2_as_eth)
        for entry in diff:
            affected[_bucket_key(entry['bucket'])] = entry['bucket']
        if _content_digest(saved) == _content_digest(decoded):
            status = 'no_change'
        elif customized and not replace_customized:
            status = 'blocked_by_customization'
        else:
            status = 'ready'
        if matched and status == 'ready':
            uncertainty.append({
                'group_identifier': group_identifier,
                'code': 'matched_links_dropped',
                'detail': 'The transaction has matched events (bridge or asset movement '
                          'links). Redecoding replaces them, so the links must be matched '
                          'again afterwards',
            })
        items.append(item | {
            'status': status,
            'decoded_digest': _content_digest(decoded),
            'event_diff': _event_diff(saved, decoded),
            'current_events': [serialize_event_summary(
                event=event,
                mapping_states=mapping_states.get(event.identifier or -1, ()),
            ) | serialize_effects(event, treat_eth2_as_eth) for event in saved],
            'proposed_events': [
                _event_content(event) | serialize_effects(event, treat_eth2_as_eth)
                for event in decoded
            ],
            'bucket_effect_diff': diff,
        })

    return _finish_preview(
        database=database,
        kind=PlanKind.REDECODE,
        items=items,
        affected=list(affected.values()),
        uncertainty=uncertainty,
    )


def _finish_preview(
        database: DBHandler,
        kind: PlanKind,
        items: list[dict[str, Any]],
        affected: list[dict[str, Any]],
        uncertainty: list[dict[str, Any]],
) -> dict[str, Any]:
    baseline = _baseline(database, affected)
    with database.conn.read_ctx() as cursor:
        processing_state = get_processing_state(cursor=cursor, database=database)
    uncertainty.append({
        'code': 'outcome_established_by_verification',
        'detail': 'Whether the affected stops and issues clear is only known after the '
                  'affected range is reprocessed. apply reprocesses it and verifies',
    })
    plan = {
        'items': items,
        'affected_buckets': affected,
        'baseline': baseline,
        'expected_issue_impact': [{
            'issue_id': issue_id,
            'expectation': 'may_change',
        } for issue_id in baseline['open_issue_ids']],
        'uncertainty': uncertainty,
        'processing_at_preview': processing_state,
        'applicable_items': sum(item['status'] == 'ready' for item in items),
    }
    return _save_plan(
        database=database,
        kind=kind,
        plan=plan,
        evidence_revision=_digest([
            item.get('saved_digest') for item in items
        ] + [item.get('decoded_digest') for item in items]),
    )


def _load_events(database: DBHandler, identifiers: list[int]) -> dict[int, HistoryBaseEntry]:
    with database.conn.read_ctx() as cursor:
        return {
            event.identifier: event  # type: ignore[misc]  # events from the db have identifiers
            for event in DBHistoryEvents(database).get_history_events_internal(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(identifiers=identifiers),
            )
        }


def preview_bridge_link(
        database: DBHandler,
        bridge_event_identifier: int,
        matched_event_identifier: int,
) -> dict[str, Any]:
    """Preview linking a bridge leg with a counterpart candidate.

    Only a candidate the matcher considers eligible can be proposed: a rejected one would need
    a judgement the plan can't make. May raise RemediationError.
    """
    events = _load_events(database, [bridge_event_identifier, matched_event_identifier])
    if (bridge_event := events.get(bridge_event_identifier)) is None or (
        matched_event := events.get(matched_event_identifier)
    ) is None:
        raise RemediationError('unknown_event', 'Both events of the link must exist')

    settings = CachedSettings().get_settings()
    with database.conn.read_ctx() as cursor:
        excluded_ids = get_already_matched_event_ids(
            cursor=cursor,
            link_type=HistoryEventLinkType.BRIDGE_MATCH,
        )
        mapping_states = get_mapping_states(cursor=cursor, events=events.values())
    if bridge_event_identifier in excluded_ids:
        raise RemediationError('already_linked', 'The bridge leg is already linked')

    tier, rejection = classify_bridge_candidate(
        bridge_event=bridge_event,
        candidate=matched_event,
        assets_in_collection=get_bridge_match_assets_in_collection(deposit=bridge_event),
        tolerance=settings.bridge_match_amount_tolerance,
        excluded_ids=excluded_ids,
    )
    if tier is None:
        raise RemediationError(
            'candidate_rejected',
            f'The matcher rejects this candidate: {rejection}',
        )

    treat_eth2_as_eth = settings.treat_eth2_as_eth
    after = apply_bridge_match_to_events(
        bridge_event=copy.deepcopy(bridge_event),
        matched_event=copy.deepcopy(matched_event),
    )
    before = (bridge_event, matched_event)
    diff = _effect_diff(before, after, treat_eth2_as_eth)
    item = {
        'bridge_event_identifier': bridge_event_identifier,
        'matched_event_identifier': matched_event_identifier,
        'tier': tier,
        'status': 'ready',
        'timestamp_ms': min(bridge_event.timestamp, matched_event.timestamp),
        'saved_digest': _saved_digest(list(before), mapping_states),
        'current_events': [
            serialize_event_summary(event) | serialize_effects(event, treat_eth2_as_eth)
            for event in before
        ],
        'proposed_events': [
            _event_content(event) | serialize_effects(event, treat_eth2_as_eth)
            for event in after
        ],
        'bucket_effect_diff': diff,
    }
    affected = {
        _bucket_key(bucket): bucket for bucket in (
            serialize_bucket(make_bucket(
                location=event.location,
                location_label=event.location_label,
                protocol=None,
                asset=event.asset.identifier,
            )) for event in before
        )
    }
    return _finish_preview(
        database=database,
        kind=PlanKind.BRIDGE_LINK,
        items=[item],
        affected=list(affected.values()),
        uncertainty=[],
    )


def _set_state(
        database: DBHandler,
        plan_id: str,
        state: PlanState,
        action: str,
        details: dict[str, Any],
        result: dict[str, Any] | None = None,
        expected_state: PlanState | None = None,
) -> bool:
    """Move the plan to state, only from expected_state when given. Returns whether it moved."""
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'UPDATE remediation_plans SET state = ?, result = COALESCE(?, result), '
            'applied_at = CASE WHEN ? THEN ? ELSE applied_at END WHERE identifier = ?' + (
                ' AND state = ?' if expected_state is not None else ''
            ),
            (
                state.value,
                None if result is None else json.dumps(result, default=str),
                state == PlanState.APPLYING,  # reprocessing after this point covers the plan
                ts_now(),
                plan_id,
                *((expected_state.value,) if expected_state is not None else ()),
            ),
        )
        if (moved := write_cursor.rowcount == 1):
            _audit(write_cursor, plan_id, action, details)
    return moved


def reject_plan(database: DBHandler, plan_id: str, reason: str) -> dict[str, Any]:
    """Record that the user declined the plan. May raise NotFoundError or RemediationError."""
    plan = get_plan(database, plan_id)
    if not _set_state(
        database=database,
        plan_id=plan_id,
        state=PlanState.REJECTED,
        action='rejected',
        details={'reason': reason},
        expected_state=PlanState.PENDING,
    ):
        raise RemediationError('plan_not_pending', f'The plan is {plan["state"]}')
    return get_plan(database, plan_id)


def _check_evidence(database: DBHandler, plan: dict[str, Any]) -> str | None:
    """Why the plan's evidence no longer holds, None if it still does."""
    for item in plan['plan']['items']:
        if item['status'] not in ('ready', 'blocked_by_customization', 'no_change'):
            continue
        if plan['kind'] == PlanKind.REDECODE:
            events = get_group_events(database, item['group_identifier'])
        else:
            events = list(_load_events(database, [
                item['bridge_event_identifier'],
                item['matched_event_identifier'],
            ]).values())
        with database.conn.read_ctx() as cursor:
            mapping_states = get_mapping_states(cursor=cursor, events=events)
        if _saved_digest(events, mapping_states) != item['saved_digest']:
            return 'The events of the plan changed since it was previewed'
    return None


def apply_plan(
        database: DBHandler,
        chains_aggregator: ChainsAggregator,
        plan_id: str,
        approval_method: str,
        approved_at: int,
) -> dict[str, Any]:
    """Apply an approved plan, reprocess the affected range and verify the outcome.

    May raise NotFoundError or RemediationError.
    """
    if approval_method not in APPROVAL_METHODS:
        raise RemediationError('approval_required', 'The plan has not been approved')

    plan = get_plan(database, plan_id)
    if plan['state'] == PlanState.EXPIRED:
        _set_state(database, plan_id, PlanState.EXPIRED, 'expired', {}, expected_state=PlanState.PENDING)  # noqa: E501
        raise RemediationError('plan_expired', 'The plan expired. Preview it again')
    if plan['state'] != PlanState.PENDING:
        raise RemediationError('plan_not_pending', f'The plan is {plan["state"]}')
    if plan['plan']['applicable_items'] == 0:
        raise RemediationError('nothing_to_apply', 'No item of the plan can be applied')
    if (stale_reason := _check_evidence(database, plan)) is not None:
        _set_state(database, plan_id, PlanState.STALE, 'stale', {'reason': stale_reason}, expected_state=PlanState.PENDING)  # noqa: E501
        raise RemediationError('plan_stale', f'{stale_reason}. Preview it again')
    if not _set_state(  # the state check makes a concurrent or repeated apply a no-op
        database=database,
        plan_id=plan_id,
        state=PlanState.APPLYING,
        action='approved',
        details={'approval_method': approval_method, 'approved_at_ts_s': approved_at},
        expected_state=PlanState.PENDING,
    ):
        raise RemediationError('plan_not_pending', 'The plan is already being applied')

    outcomes = (
        _apply_redecode(database, chains_aggregator, plan) if plan['kind'] == PlanKind.REDECODE
        else _apply_bridge_link(database, plan)
    )
    applied = [x for x in outcomes if x['outcome'] in ('applied', 'applied_with_differences')]
    timestamps = [item['timestamp_ms'] for item in plan['plan']['items'] if 'timestamp_ms' in item]
    reprocessing = 'not_needed'
    if len(applied) != 0 and len(timestamps) != 0:
        try:
            reprocessing = 'completed' if process_historical_balances(
                database=database,
                msg_aggregator=database.msg_aggregator,
                from_ts=TimestampMS(min(timestamps)),
                chains_aggregator=chains_aggregator,
            ) is True else 'deferred_another_pass_running'
        except (RemoteError, DeserializationError) as e:
            log.error('Reprocessing after applying remediation plan failed', plan_id=plan_id, error=str(e))  # noqa: E501
            reprocessing = 'failed'

    state = (
        PlanState.APPLIED if len(applied) == len(outcomes) and len(outcomes) != 0 else
        PlanState.PARTIALLY_APPLIED if len(applied) != 0 else PlanState.FAILED
    )
    result = {'items': outcomes, 'reprocessing': reprocessing}
    _set_state(
        database=database,
        plan_id=plan_id,
        state=state,
        action='applied',
        details={'outcomes': [x['outcome'] for x in outcomes], 'reprocessing': reprocessing},
        result=result,
    )
    return verify_plan(database, plan_id)


def _apply_redecode(
        database: DBHandler,
        chains_aggregator: ChainsAggregator,
        plan: dict[str, Any],
) -> list[dict[str, Any]]:
    outcomes = []
    for item in plan['plan']['items']:
        if item['status'] != 'ready':
            outcomes.append({
                'group_identifier': item['group_identifier'],
                'outcome': 'skipped',
                'reason': item['status'],
            })
            continue

        chain_id = ChainID.deserialize(item['chain_id'])
        decoder = chains_aggregator.get_evm_manager(chain_id).transactions_decoder  # type: ignore[arg-type]  # the chain was checked at preview
        apply_exceptions: tuple[type[Exception], ...] = (
            RemoteError,
            DeserializationError,
            InputError,
            *decoder.possible_decoding_exceptions,
        )
        try:
            decoder.decode_transaction_hashes(
                ignore_cache=True,
                tx_hashes=[deserialize_evm_tx_hash(item['tx_hash'])],
                delete_customized=item['replace_customized'],
            )
        except apply_exceptions as e:
            outcomes.append({
                'group_identifier': item['group_identifier'],
                'outcome': 'failed',
                'reason': str(e),
            })
            continue

        events = get_group_events(database, item['group_identifier'])
        outcomes.append({
            'group_identifier': item['group_identifier'],
            'outcome': (
                'applied' if _content_digest(events) == item['decoded_digest']
                else 'applied_with_differences'
            ),
        })
    return outcomes


def _apply_bridge_link(database: DBHandler, plan: dict[str, Any]) -> list[dict[str, Any]]:
    item = plan['plan']['items'][0]
    events = _load_events(database, [
        item['bridge_event_identifier'],
        item['matched_event_identifier'],
    ])
    update_bridge_matched_event(
        events_db=DBHistoryEvents(database),
        bridge_event=events[item['bridge_event_identifier']],
        matched_event=events[item['matched_event_identifier']],
    )
    return [{
        'bridge_event_identifier': item['bridge_event_identifier'],
        'matched_event_identifier': item['matched_event_identifier'],
        'outcome': 'applied',
    }]


def verify_plan(database: DBHandler, plan_id: str) -> dict[str, Any]:
    """Whether the plan's buckets were re-evaluated and repaired, read from the stops.

    A bucket whose stop is gone was repaired; one whose stop is at the same event was not; a
    stop at another event is a new problem revealed by the repair. Buckets are only judged
    once a processing pass covered them after the plan was applied: before that the verdict
    is ``not_reevaluated``, whatever the issues say. May raise NotFoundError.
    """
    plan = get_plan(database, plan_id)
    with database.conn.read_ctx() as cursor:
        stops = get_bucket_stops(cursor)
        processing_state = get_processing_state(cursor=cursor, database=database)
        issue_states: dict[int, str] = {}
        if len(ids := plan['plan']['baseline']['open_issue_ids']) != 0:
            issue_states = dict(cursor.execute(
                f'SELECT id, state FROM data_issues WHERE id IN ({",".join("?" * len(ids))})',
                ids,
            ))
        new_issues = [row[0] for row in cursor.execute(
            'SELECT id, location, location_label, protocol, asset FROM data_issues '
            'WHERE created_at >= ? AND state IN (?, ?, ?)',
            (
                plan['applied_at_ts_s'] or ts_now(),
                IssueState.OPEN,
                IssueState.UNRESOLVED,
                IssueState.AUTO_REMEDIATING,
            ),
        ) if row[0] not in ids and make_bucket_key(*row[1:]) in {
            _bucket_key(bucket) for bucket in plan['plan']['affected_buckets']
        }]

    if plan['state'] not in (PlanState.APPLIED, PlanState.PARTIALLY_APPLIED):
        return plan | {'verification': {'verdict': 'not_applied'}}

    baseline_stops = {
        _bucket_key(entry['bucket']): entry for entry in plan['plan']['baseline']['stops']
    }
    earliest = min(
        (item['timestamp_ms'] for item in plan['plan']['items'] if 'timestamp_ms' in item),
        default=None,
    )
    reevaluated = (
        (last := processing_state['last_processing_ts_s']) is not None and
        last >= plan['applied_at_ts_s'] and (
            processing_state['stale_from_ts_ms'] is None or
            (earliest is not None and processing_state['stale_from_ts_ms'] > earliest)
        )
    )
    buckets = []
    for bucket in plan['plan']['affected_buckets']:
        key = _bucket_key(bucket)
        before, now = baseline_stops.get(key), stops.get(key)
        if not reevaluated:
            outcome = 'not_reevaluated'
        elif before is None and now is None:
            outcome = 'no_stop'
        elif before is not None and now is None:
            outcome = 'stop_cleared'
        elif before is not None and now is not None and before['event_identifier'] == now.event_identifier:  # noqa: E501
            outcome = 'stop_persisted'
        elif before is not None:
            outcome = 'stop_moved'
        else:
            outcome = 'new_stop'
        buckets.append({
            'bucket': bucket,
            'outcome': outcome,
            'stop_event_identifier': None if now is None else now.event_identifier,
            'stop_event_timestamp_ms': None if now is None else now.event_timestamp,
        })

    outcomes = {entry['outcome'] for entry in buckets}
    if not reevaluated:
        verdict = 'not_reevaluated'
    elif outcomes & {'new_stop', 'stop_moved'} or len(new_issues) != 0:
        verdict = 'new_problems_revealed'
    elif 'stop_persisted' in outcomes:
        verdict = 'not_repaired' if 'stop_cleared' not in outcomes else 'partially_repaired'
    else:
        verdict = 'repaired'

    verification = {
        'verdict': verdict,
        'reevaluated': reevaluated,
        'processing': processing_state,
        'buckets': buckets,
        'baseline_issues': [
            {'issue_id': issue_id, 'state': issue_states.get(issue_id, 'deleted')}
            for issue_id in plan['plan']['baseline']['open_issue_ids']
        ],
        'new_open_issue_ids': new_issues,
        'interpretation': 'The verdict comes from the bucket processing stops, not from issue '
                          'states: a dismissed or resolved issue does not mean repaired data',
    }
    with database.user_write() as write_cursor:
        _audit(write_cursor, plan_id, 'verified', {'verdict': verdict})
    return get_plan(database, plan_id) | {'verification': verification}
