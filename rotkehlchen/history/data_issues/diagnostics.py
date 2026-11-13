"""Read-only diagnostics of the historical balance engine.

These explain why a bucket stopped, what each event did to it and what the inbox issues rest
on, so that an agent or a user does not have to reconstruct the engine's state by hand. They
reuse the engine's own rules (Bucket.effects_with_rule) instead of reimplementing them.

Every amount is computed with decimal arithmetic and returned as a decimal string. Timestamps
carry their unit in the key name (``_ms`` or ``_s``). Nothing here writes, refreshes or
queries a remote: a diagnosis only reads the evidence already in the database, and says so
when that evidence is missing, stale or incomplete instead of treating it as zero.
"""
import logging
from collections import Counter, defaultdict
from itertools import starmap
from typing import TYPE_CHECKING, Any, Final, Literal

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.types import AssetFlag
from rotkehlchen.constants import ZERO
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.constants import TX_DECODED, HistoryMappingState
from rotkehlchen.db.filtering import DataIssuesFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.feature_flags import is_accounting_update_enabled
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.data_issues.bucket_checks import BucketStatus
from rotkehlchen.history.data_issues.bucket_state import (
    BucketStop,
    get_bucket_stops,
    make_bucket_key,
    wallet_bucket_assets,
)
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.reconciliation import get_reconciliation_report
from rotkehlchen.history.events.structures.types import EventDirection
from rotkehlchen.locations.chains import EVM_LOCATIONS
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tasks.historical_balances import Bucket
from rotkehlchen.types import EventMetricKey, TimestampMS
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.history.data_issues.types import DataIssue
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DEFAULT_TRACE_PAGE_SIZE: Final = 200
MAX_TRACE_PAGE_SIZE: Final = 1000
MAX_LISTED_STOPS: Final = 50
# A shortfall this small relative to the amount moved is more likely decimal residue (a
# rounded amount on one leg) than missing history.
RESIDUE_RELATIVE_THRESHOLD: Final = FVal('0.000001')

type TraceRowStatus = Literal[
    'applied',
    'stop',
    'negative_awaiting_rebase_reconciliation',
    'skipped_after_stop',
]


def serialize_bucket(bucket: Bucket) -> dict[str, Any]:
    return {
        'location': bucket.location,
        'location_label': bucket.location_label,
        'protocol': bucket.protocol,
        'asset': bucket.asset,
    }


def make_bucket(
        location: str,
        location_label: str | None,
        protocol: str | None,
        asset: str,
) -> Bucket:
    return Bucket(
        location=location,
        location_label=location_label or None,
        protocol=protocol or None,
        asset=asset,
    )


def serialize_event_summary(
        event: HistoryBaseEntry,
        mapping_states: Sequence[HistoryMappingState] = (),
) -> dict[str, Any]:
    """The facts of an event a diagnosis needs, without its free text notes.

    Notes and other free text are left out on purpose: they can carry attacker-controlled
    token names and links, and the structured fields already state what happened.
    """
    return {
        'event_identifier': event.identifier,
        'group_identifier': event.group_identifier,
        'tx_ref': None if (tx_ref := getattr(event, 'tx_ref', None)) is None else str(tx_ref),
        'entry_type': event.entry_type.serialize(),
        'location': event.location,
        'location_label': event.location_label,
        'address': getattr(event, 'address', None),
        'timestamp_ms': event.timestamp,
        'sequence_index': event.sequence_index,
        'event_type': event.event_type.serialize(),
        'event_subtype': event.event_subtype.serialize(),
        'asset': event.asset.identifier,
        'amount': str(event.amount),
        'counterparty': getattr(event, 'counterparty', None),
        'mapping_states': [state.serialize() for state in mapping_states],
        'metadata_keys': sorted((event.extra_data or {}).keys()),
    }


def serialize_effects(
        event: HistoryBaseEntry,
        treat_eth2_as_eth: bool,
) -> dict[str, Any]:
    """The rule deciding the event's balance effects and the signed effect on each bucket."""
    rule, effects = Bucket.effects_with_rule(event=event, treat_eth2_as_eth=treat_eth2_as_eth)
    return {
        'rule': rule.value,
        'effects': [{
            'bucket': serialize_bucket(bucket),
            'direction': 'in' if direction == EventDirection.IN else 'out',
            'signed_amount': str(event.amount if direction == EventDirection.IN else -event.amount),  # noqa: E501
        } for bucket, direction in effects],
    }


def get_mapping_states(
        cursor: DBCursor,
        events: Iterable[HistoryBaseEntry],
) -> dict[int, list[HistoryMappingState]]:
    if len(identifiers := [x.identifier for x in events if x.identifier is not None]) == 0:
        return {}

    return DBHistoryEvents.get_event_mapping_states(
        cursor=cursor,
        location=None,
        entry_identifiers=identifiers,
    )


def get_processing_state(cursor: DBCursor, database: DBHandler) -> dict[str, Any]:
    """Freshness of the derived balances: when they were processed and what is stale since.

    ``stale_from_ts_ms`` is the earliest event timestamp whose derived balances are out of
    date, None when nothing is stale. ``revision`` changes whenever events are modified, so a
    caller can tell whether two diagnoses looked at the same history.
    """
    last_processing = database.get_static_cache(
        cursor=cursor,
        name=DBCacheStatic.LAST_HISTORICAL_BALANCE_PROCESSING_TS,
    )
    stale_from = database.get_static_cache(
        cursor=cursor,
        name=DBCacheStatic.STALE_BALANCES_FROM_TS,
    )
    modification = database.get_static_cache(
        cursor=cursor,
        name=DBCacheStatic.STALE_BALANCES_MODIFICATION_TS,
    )
    return {
        'last_processing_ts_s': last_processing,
        'stale_from_ts_ms': stale_from,
        'revision': f'{last_processing or 0}:{modification or 0}',
        'observed_at_ts_s': ts_now(),
    }


def _count_pending_decoding(cursor: DBCursor) -> dict[str, int]:
    """Saved EVM transactions of tracked accounts that are not decoded yet, per chain id."""
    return {
        str(chain_id): count for chain_id, count in cursor.execute(
            'SELECT T.chain_id, COUNT(DISTINCT T.identifier) FROM evm_transactions AS T '
            'INNER JOIN evmtx_address_mappings AS M ON M.tx_id = T.identifier '
            'WHERE NOT EXISTS (SELECT 1 FROM evm_tx_mappings AS D '
            'WHERE D.tx_id = T.identifier AND D.value = ?) GROUP BY T.chain_id',
            (TX_DECODED,),
        )
    }


def _archive_node_capabilities(cursor: DBCursor) -> dict[str, dict[str, int]]:
    """Active RPC nodes per chain by whether they serve archive state, from their saved probe.

    Rebasing token reconciliation and the divergence search query past balances, which only an
    archive node serves. ``unknown`` counts nodes whose capabilities were not probed yet.
    """
    capabilities: dict[str, dict[str, int]] = defaultdict(
        lambda: {'archive': 0, 'not_archive': 0, 'unknown': 0},
    )
    for blockchain, is_archive, count in cursor.execute(
        'SELECT blockchain, is_archive, COUNT(*) FROM rpc_nodes WHERE active = 1 '
        'GROUP BY blockchain, is_archive',
    ):
        capabilities[blockchain][
            'unknown' if is_archive is None else 'archive' if is_archive else 'not_archive'
        ] += count
    return dict(sorted(capabilities.items()))


def _serialize_stop(key: tuple[str, str, str, str], stop: BucketStop) -> dict[str, Any]:
    location, label, protocol, asset = key
    return {
        'bucket': serialize_bucket(make_bucket(location, label, protocol, asset)),
        'event_identifier': stop.event_identifier,
        'group_identifier': stop.group_identifier,
        'event_timestamp_ms': stop.event_timestamp,
        'derived_balance_before_event': str(stop.derived_balance_before_event),
        'negative_amount': str(stop.negative_amount),
        'event_deleted': stop.group_identifier is None,
    }


def get_accounting_health(database: DBHandler) -> dict[str, Any]:
    """Whether the derived balances can be trusted, and why not when they can't.

    ``status`` is the first of these that applies: ``disabled``, ``unprocessed`` (never
    processed), ``processing_pending`` (events changed since the last pass), ``blocked``
    (a bucket stopped), ``mismatch`` (a comparison disagrees with the chain), ``unverified``
    (some buckets were never compared or can't be), ``healthy``. An unverified bucket is not
    a healthy one: only ``reconciled`` buckets have been checked against an observation.
    """
    if is_accounting_update_enabled() is False:
        return {'status': 'disabled', 'feature_enabled': False}

    settings = CachedSettings().get_settings()
    with database.conn.read_ctx() as cursor:
        processing_state = get_processing_state(cursor=cursor, database=database)
        stops = get_bucket_stops(cursor)
        pending_decoding = _count_pending_decoding(cursor)
        issue_counts: Counter[tuple[str, str]] = Counter({
            (kind, state): count for kind, state, count in cursor.execute(
                'SELECT kind, state, COUNT(*) FROM data_issues GROUP BY kind, state',
            )
        })
        last_remediation = database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.LAST_DATA_ISSUE_REMEDIATION_TS,
        )
        last_detection = database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.LAST_CURRENT_BALANCE_DETECTION_TS,
        )
        archive_nodes = _archive_node_capabilities(cursor)

    report = get_reconciliation_report(database=database)
    reason_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for bucket in report.all_buckets:
        for reason in bucket.reasons:
            reason_counts[bucket.status.value][reason.value] += 1

    totals = {status.value: count for status, count in report.totals.items()}
    if processing_state['last_processing_ts_s'] is None:
        status = 'unprocessed'
    elif processing_state['stale_from_ts_ms'] is not None or report.processing:
        status = 'processing_pending'
    elif len(stops) != 0:
        status = 'blocked'
    elif totals.get(BucketStatus.MISMATCH.value, 0) != 0:
        status = 'mismatch'
    elif (
        totals.get(BucketStatus.PENDING.value, 0) != 0 or
        totals.get(BucketStatus.NOT_COMPARED.value, 0) != 0 or
        sum(pending_decoding.values()) != 0
    ):
        status = 'unverified'
    else:
        status = 'healthy'

    sorted_stops = sorted(stops.items(), key=lambda item: item[1].event_timestamp)
    return {
        'status': status,
        'feature_enabled': True,
        'settings': {
            'treat_eth2_as_eth': settings.treat_eth2_as_eth,
            'auto_create_profit_events': settings.auto_create_profit_events,
            'bridge_match_time_range_s': settings.bridge_match_time_range,
            'bridge_match_amount_tolerance': str(settings.bridge_match_amount_tolerance),
            'reconciliation_tolerance': str(settings.asset_movement_amount_tolerance),
        },
        'processing': processing_state | {
            'has_unprocessed_events': report.processing,
            'last_remediation_ts_s': last_remediation,
            'last_current_balance_detection_ts_s': last_detection,
        },
        'comparison_coverage': {
            'buckets_total': sum(totals.values()),
            'counts': totals,
            'reason_counts': {
                status_name: dict(sorted(counts.items()))
                for status_name, counts in sorted(reason_counts.items())
            },
        },
        'stops': {
            'count': len(stops),
            'entries': list(starmap(_serialize_stop, sorted_stops[:MAX_LISTED_STOPS])),
            'truncated': len(stops) > MAX_LISTED_STOPS,
        },
        'pending_decoding': {
            'transactions_by_chain_id': pending_decoding,
            'total': sum(pending_decoding.values()),
        },
        'issues': {
            'counts': [
                {'kind': kind, 'state': state, 'count': count}
                for (kind, state), count in sorted(issue_counts.items())
            ],
            'open_total': sum(
                count for (_, state), count in issue_counts.items()
                if state in (IssueState.OPEN, IssueState.UNRESOLVED, IssueState.AUTO_REMEDIATING)
            ),
        },
        'capabilities': {
            # Diagnosis never queries a node. Rebasing reconciliation and divergence search do,
            # and need an archive node; their results show up as issues and observations.
            'diagnosis_uses_network': False,
            'archive_nodes_by_chain': archive_nodes,
            'archive_queries_possible_for': [
                chain for chain, counts in archive_nodes.items() if counts['archive'] != 0
            ],
        },
    }


def _bucket_event_assets(bucket: Bucket, treat_eth2_as_eth: bool) -> tuple[Asset, ...]:
    """Every asset whose events can land in the bucket: its own, the ones swapped for it and
    ETH2 when it is aggregated under ETH."""
    with GlobalDBHandler().conn.read_ctx() as cursor:
        swapped = [row[0] for row in cursor.execute(
            'SELECT identifier FROM common_asset_details WHERE swapped_for = ?',
            (bucket.asset,),
        )]
    return tuple(Asset(identifier) for identifier in dict.fromkeys((
        *wallet_bucket_assets(asset=bucket.asset, treat_eth2_as_eth=treat_eth2_as_eth),
        *swapped,
    )))


def _get_stored_metrics(
        cursor: DBCursor,
        bucket: Bucket,
) -> dict[tuple[int, str], FVal]:
    """The metric values the last processing pass stored for the bucket, per event and key."""
    return {
        (event_identifier, metric_key): FVal(value)
        for event_identifier, metric_key, value in cursor.execute(
            'SELECT event_identifier, metric_key, metric_value FROM event_metrics '
            'WHERE location = ? AND location_label IS ? AND protocol IS ? AND asset = ?',
            (bucket.location, bucket.location_label, bucket.protocol, bucket.asset),
        )
    }


def _trace_rows(
        database: DBHandler,
        bucket: Bucket,
        from_ts: TimestampMS | None = None,
) -> tuple[list[dict[str, Any]], BucketStop | None, dict[str, Any]]:
    """Replay the events of one bucket the way the processor applies them, without writing.

    Each row carries the exact balance before and after the effect, the rule that produced it
    and the balance the last processing pass stored for that event, so a row whose replayed
    balance disagrees with the stored one reveals metrics that are out of date.

    Rebasing tokens are reconciled against on-chain balances during processing, which a read
    can't redo. The stored rebase yield is added back instead and the trace says so.
    """
    settings = CachedSettings()
    treat_eth2_as_eth = settings.get_entry('treat_eth2_as_eth') is True
    rebasing = bucket.asset in GlobalDBHandler.get_asset_ids_with_flag(AssetFlag.REBASING)
    event_filter = HistoryEventFilterQuery.make(
        order_by_rules=[
            ('timestamp', True),
            ('sequence_index', True),
            ('history_events_identifier', True),
        ],
        location=bucket.location,  # type: ignore[arg-type]  # the bucket location is a location identifier
        assets=_bucket_event_assets(bucket=bucket, treat_eth2_as_eth=treat_eth2_as_eth),
        exclude_ignored_assets=True,
        exclude_untracked_withdrawals=True,
    )
    with database.conn.read_ctx() as cursor:
        events = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=event_filter,
        )
        stored = _get_stored_metrics(cursor=cursor, bucket=bucket)
        stop = get_bucket_stops(cursor).get(make_bucket_key(
            location=bucket.location,
            location_label=bucket.location_label,
            protocol=bucket.protocol,
            asset=bucket.asset,
        ))
        mapping_states = get_mapping_states(cursor=cursor, events=events)

    rows: list[dict[str, Any]] = []
    balance, stopped, awaiting_rebase = ZERO, False, False
    stored_mismatches = 0
    balance_metric = EventMetricKey.BALANCE.serialize()
    rebase_metric = EventMetricKey.REBASE_YIELD.serialize()
    for event in events:
        rule, effects = Bucket.effects_with_rule(event=event, treat_eth2_as_eth=treat_eth2_as_eth)
        for effect_bucket, direction in effects:
            if effect_bucket != bucket:
                continue

            signed = event.amount if direction == EventDirection.IN else -event.amount
            before = balance
            status: TraceRowStatus
            rebase_yield = None
            if stopped:
                status, after = 'skipped_after_stop', balance
            else:
                after = before + signed
                if (
                    event.identifier is not None and
                    (rebase_yield := stored.get((event.identifier, rebase_metric))) is not None
                ):
                    after += rebase_yield
                    awaiting_rebase = False
                if after < ZERO and rebasing:
                    status, awaiting_rebase = 'negative_awaiting_rebase_reconciliation', True
                elif after < ZERO:
                    status, stopped = 'stop', True
                else:
                    status = 'applied'
                balance = after

            stored_balance = None if event.identifier is None else stored.get(
                (event.identifier, balance_metric),
            )
            if status == 'applied' and stored_balance is not None and stored_balance != after:
                stored_mismatches += 1
            if from_ts is not None and event.timestamp < from_ts:
                continue

            rows.append({
                'event_identifier': event.identifier,
                'group_identifier': event.group_identifier,
                'timestamp_ms': event.timestamp,
                'sequence_index': event.sequence_index,
                'event_type': event.event_type.serialize(),
                'event_subtype': event.event_subtype.serialize(),
                'event_asset': event.asset.identifier,
                'counterparty': getattr(event, 'counterparty', None),
                'rule': rule.value,
                'direction': 'in' if direction == EventDirection.IN else 'out',
                'signed_amount': str(signed),
                'balance_before': str(before),
                'balance_after': str(after),
                'rebase_yield': None if rebase_yield is None else str(rebase_yield),
                'stored_balance': None if stored_balance is None else str(stored_balance),
                'status': status,
                'customized': HistoryMappingState.CUSTOMIZED in mapping_states.get(
                    event.identifier or -1, (),
                ),
            })

    return rows, stop, {
        'rebasing_asset': rebasing,
        'awaiting_rebase_reconciliation': awaiting_rebase,
        'final_balance': str(balance),
        'stored_balance_mismatches': stored_mismatches,
    }


def trace_bucket(
        database: DBHandler,
        bucket: Bucket,
        from_ts: TimestampMS | None = None,
        limit: int = DEFAULT_TRACE_PAGE_SIZE,
        offset: int | None = None,
) -> dict[str, Any]:
    """The ordered effects of every event on one bucket, with exact running balances.

    Without an explicit offset the page starts a few rows before the stop, when there is one,
    so the event that stopped the bucket and what led to it come first.
    """
    rows, stop, summary = _trace_rows(database=database, bucket=bucket, from_ts=from_ts)
    limit = min(max(limit, 1), MAX_TRACE_PAGE_SIZE)
    stop_index = next((idx for idx, row in enumerate(rows) if row['status'] == 'stop'), None)
    if offset is None:
        offset = 0 if stop_index is None else max(stop_index - 10, 0)
    offset = max(offset, 0)
    with database.conn.read_ctx() as cursor:
        processing_state = get_processing_state(cursor=cursor, database=database)

    return {
        'bucket': serialize_bucket(bucket),
        'processing': processing_state,
        'summary': summary | {
            'effects_total': len(rows),
            'stop_row_index': stop_index,
            'skipped_after_stop': sum(row['status'] == 'skipped_after_stop' for row in rows),
            'derived_balances_stale': processing_state['stale_from_ts_ms'] is not None,
        },
        'stop': None if stop is None else _serialize_stop(
            key=make_bucket_key(
                location=bucket.location,
                location_label=bucket.location_label,
                protocol=bucket.protocol,
                asset=bucket.asset,
            ),
            stop=stop,
        ),
        'rows': rows[offset:offset + limit],
        'pagination': {
            'offset': offset,
            'limit': limit,
            'total': len(rows),
            'truncated': offset + limit < len(rows),
        },
    }


def serialize_issue(issue: DataIssue) -> dict[str, Any]:
    return {
        'id': issue.id,
        'kind': issue.kind,
        'state': issue.state,
        'severity': issue.severity,
        'bucket': serialize_bucket(make_bucket(
            location=issue.location,
            location_label=issue.location_label,
            protocol=issue.protocol,
            asset=issue.asset,
        )),
        'group_identifier': issue.group_identifier,
        'event_identifier': issue.payload.get('event_identifier'),
        'ts_start_ms': issue.ts_start,
        'ts_end_ms': issue.ts_end,
        'created_at_ts_s': issue.created_at,
        'resolved_at_ts_s': issue.resolved_at,
        'auto_remediation_attempts': len(issue.auto_remediation_attempts),
    }


def list_data_issues(
        database: DBHandler,
        filter_query: DataIssuesFilterQuery,
) -> dict[str, Any]:
    """The issues matching the filter, with the issues of one transaction grouped together.

    ``groups`` gathers the issues by the transaction (event group) they were raised on, since
    several issues of one transaction usually share a cause. That a group shares a cause is a
    hypothesis, never established by the grouping itself.
    """
    manager = DataIssuesManager(database)
    issues = manager.list_issues(filter_query)
    with database.conn.read_ctx() as cursor:
        event_groups = _event_groups(
            cursor=cursor,
            event_identifiers=[
                event_id for issue in issues
                if isinstance(event_id := issue.payload.get('event_identifier'), int)
            ],
        )

    serialized = []
    by_group: dict[str, list[int]] = defaultdict(list)
    for issue in issues:
        entry = serialize_issue(issue)
        if entry['group_identifier'] is None and entry['event_identifier'] is not None:
            entry['group_identifier'] = event_groups.get(entry['event_identifier'])
        if (group := entry['group_identifier']) is not None:
            by_group[group].append(issue.id)
        serialized.append(entry)

    return {
        'entries': serialized,
        'entries_found': manager.count_issues(filter_query),
        'groups': [
            {'group_identifier': group, 'issue_ids': ids, 'shared_cause': 'hypothesis'}
            for group, ids in by_group.items() if len(ids) > 1
        ],
    }


def _event_groups(cursor: DBCursor, event_identifiers: Sequence[int]) -> dict[int, str]:
    if len(event_identifiers) == 0:
        return {}

    placeholders = ','.join('?' * len(event_identifiers))
    return dict(cursor.execute(
        f'SELECT identifier, group_identifier FROM history_events '
        f'WHERE identifier IN ({placeholders})',
        tuple(event_identifiers),
    ))


def _get_event(database: DBHandler, event_identifier: int) -> HistoryBaseEntry | None:
    with database.conn.read_ctx() as cursor:
        events = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(identifiers=[event_identifier]),
        )
    return events[0] if len(events) == 1 else None


def get_group_events(database: DBHandler, group_identifier: str) -> list[HistoryBaseEntry]:
    with database.conn.read_ctx() as cursor:
        return DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                group_identifiers=[group_identifier],
                order_by_rules=[('sequence_index', True)],
            ),
        )


def _pending_decoding_for_account(
        database: DBHandler,
        location: str,
        location_label: str | None,
) -> int | None:
    """Undecoded transactions of the account, None when that can't apply to it."""
    if location not in EVM_LOCATIONS or location_label is None:
        return None

    with database.conn.read_ctx() as cursor:
        return cursor.execute(
            'SELECT COUNT(DISTINCT M.tx_id) FROM evmtx_address_mappings AS M '
            'INNER JOIN evm_transactions AS T ON T.identifier = M.tx_id '
            'WHERE M.address = ? AND NOT EXISTS (SELECT 1 FROM evm_tx_mappings AS D '
            'WHERE D.tx_id = M.tx_id AND D.value = ?)',
            (location_label, TX_DECODED),
        ).fetchone()[0]


def _action(tool: str, why: str, **arguments: Any) -> dict[str, Any]:
    return {'tool': tool, 'arguments': arguments, 'why': why}


def _explain_negative_balance(
        database: DBHandler,
        issue: DataIssue,
        bucket: Bucket,
        explanation: dict[str, Any],
) -> None:
    payload = issue.payload
    treat_eth2_as_eth = CachedSettings().get_entry('treat_eth2_as_eth') is True
    facts, hypotheses = explanation['facts'], explanation['hypotheses']
    if (balance_before := payload.get('derived_balance_before_event')) is not None:
        facts['derived_balance_before_event'] = balance_before
    if (negative := payload.get('in_memory_negative_amount')) is not None:
        facts['balance_after_event'] = negative
        facts['shortfall'] = str(-FVal(negative))
    if payload.get('reason') == 'untracked_exchange':
        facts['withdrawal_from_untracked_exchange'] = True

    event_identifier = payload.get('event_identifier')
    if not isinstance(event_identifier, int) or (
        trigger := _get_event(database, event_identifier)
    ) is None:
        explanation['missing_prerequisites'].append({
            'code': 'trigger_event_missing',
            'detail': 'The event that raised the issue no longer exists',
        })
        return

    group_events = get_group_events(database, trigger.group_identifier)
    with database.conn.read_ctx() as cursor:
        mapping_states = get_mapping_states(cursor=cursor, events=group_events)
    explanation['trigger_event'] = serialize_event_summary(
        event=trigger,
        mapping_states=mapping_states.get(event_identifier, ()),
    ) | serialize_effects(event=trigger, treat_eth2_as_eth=treat_eth2_as_eth)
    explanation['same_transaction_effects_on_bucket'] = [
        {
            'event_identifier': event.identifier,
            'sequence_index': event.sequence_index,
            'event_type': event.event_type.serialize(),
            'event_subtype': event.event_subtype.serialize(),
            'rule': rule.value,
            'signed_amount': str(event.amount if direction == EventDirection.IN else -event.amount),  # noqa: E501
        }
        for event in group_events
        for rule, effects in (Bucket.effects_with_rule(event, treat_eth2_as_eth),)
        for effect_bucket, direction in effects
        if effect_bucket == bucket
    ]

    rows, stop, summary = _trace_rows(database=database, bucket=bucket)
    if stop is not None:
        facts['bucket_stopped_at_this_event'] = stop.event_identifier == event_identifier
        facts['bucket_stop_event_timestamp_ms'] = stop.event_timestamp
    else:
        facts['bucket_stopped_at_this_event'] = False
    later = [row for row in rows if row['status'] == 'skipped_after_stop']
    explanation['affected_later_history'] = {
        'events_not_applied': len(later),
        'first_timestamp_ms': later[0]['timestamp_ms'] if later else None,
        'last_timestamp_ms': later[-1]['timestamp_ms'] if later else None,
        'replayed_final_balance': summary['final_balance'],
    }
    if stop is None and issue.state not in (IssueState.RESOLVED, IssueState.DISMISSED):
        explanation['confirmed_conflicts'].append({
            'code': 'open_issue_without_stop',
            'detail': 'The issue is open but the bucket has no processing stop anymore, so '
                      'the last processing pass did not reproduce the negative balance',
        })
    if stop is not None and issue.state in (IssueState.RESOLVED, IssueState.DISMISSED):
        explanation['confirmed_conflicts'].append({
            'code': 'closed_issue_but_bucket_still_stopped',
            'detail': f'The issue is {issue.state} but the bucket is still stopped. '
                      'Dismissing or resolving an issue does not repair the history',
        })

    applied_before = [
        row for row in rows
        if row['status'] == 'applied' and row['timestamp_ms'] <= trigger.timestamp
    ]
    if not any(row['direction'] == 'in' for row in applied_before):
        hypotheses.append({
            'code': 'missing_inflow_history',
            'detail': 'No event before the trigger added this asset to the bucket. The '
                      'inflow may be undecoded, in an unsynced range, or from an untracked '
                      'account or exchange',
            'basis': ['trace_bucket rows before the trigger event'],
        })
    if (
        (shortfall := facts.get('shortfall')) is not None and
        trigger.amount != ZERO and
        FVal(shortfall) <= trigger.amount * RESIDUE_RELATIVE_THRESHOLD
    ):
        hypotheses.append({
            'code': 'decimal_residue',
            'detail': f'The shortfall {shortfall} is negligible next to the amount moved '
                      f'{trigger.amount}. A rounded amount on one leg, rather than missing '
                      'history, would explain it',
            'basis': ['shortfall', 'trigger_event.amount'],
        })
    if any(
            HistoryMappingState.CUSTOMIZED in states for states in mapping_states.values()
    ):
        hypotheses.append({
            'code': 'customized_transaction',
            'detail': 'The transaction has customized events, whose effects the current '
                      'decoders would not necessarily produce',
            'basis': ['mapping_states of the transaction events'],
        })
    if (
        (attempts := issue.auto_remediation_attempts) and
        (last_result := attempts[-1].get('result')) is not None
    ):
        facts['last_redecode_comparison'] = last_result

    explanation['next_actions'].extend([
        _action('trace_bucket', 'See every effect on the bucket up to and after the stop', bucket=serialize_bucket(bucket)),  # noqa: E501
        _action('inspect_transaction', 'Compare the decoded effects with the receipt transfers', group_identifier=trigger.group_identifier),  # noqa: E501
        _action('preview_remediation', 'See what the current decoders would change', group_identifiers=[trigger.group_identifier]),  # noqa: E501
    ])


def explain_data_issue(database: DBHandler, issue_id: int) -> dict[str, Any]:
    """Explain one issue: the facts it rests on, hypotheses about its cause, conflicts between
    the issue and the bucket's actual state, missing prerequisites and next steps.

    May raise NotFoundError if there is no such issue.
    """
    issue = DataIssuesManager(database).get_issue(issue_id)
    bucket = make_bucket(
        location=issue.location,
        location_label=issue.location_label,
        protocol=issue.protocol,
        asset=issue.asset,
    )
    with database.conn.read_ctx() as cursor:
        processing_state = get_processing_state(cursor=cursor, database=database)

    explanation: dict[str, Any] = {
        'issue': serialize_issue(issue),
        'processing': processing_state,
        'facts': {},
        'hypotheses': [],
        'confirmed_conflicts': [],
        'missing_prerequisites': [],
        'next_actions': [],
        'remediation_history': [{
            key: value for key, value in attempt.items() if key != 'transactions'
        } for attempt in issue.auto_remediation_attempts],
    }
    if processing_state['stale_from_ts_ms'] is not None:
        explanation['missing_prerequisites'].append({
            'code': 'derived_balances_stale',
            'detail': 'Events changed since the last processing pass, so derived balances '
                      'from stale_from_ts_ms on may not reflect them yet',
        })
    if (pending := _pending_decoding_for_account(
        database=database,
        location=issue.location,
        location_label=bucket.location_label,
    )):
        explanation['missing_prerequisites'].append({
            'code': 'pending_decoding',
            'detail': f'{pending} transactions of the account are not decoded yet',
        })

    if issue.kind in (IssueKind.NEGATIVE_BALANCE, IssueKind.REBASING_TOKEN):
        _explain_negative_balance(
            database=database,
            issue=issue,
            bucket=bucket,
            explanation=explanation,
        )
        if issue.kind == IssueKind.REBASING_TOKEN:
            explanation['facts']['rebasing_query_failure'] = issue.payload.get('reason')
            explanation['facts']['block_number'] = issue.payload.get('block_number')
            if issue.payload.get('reason') == 'archive_node_unavailable':
                explanation['missing_prerequisites'].append({
                    'code': 'archive_node_unavailable',
                    'detail': 'Reconciling a rebasing balance needs an archive node',
                })
    elif issue.kind == IssueKind.CURRENT_BALANCE_MISMATCH:
        payload = issue.payload
        explanation['facts'] |= {
            'derived_balance': payload.get('derived_balance'),
            'observed_balance': payload.get('observed_balance'),
            'delta': payload.get('delta'),
            'observed_at_ts_s': payload.get('queried_at_ts'),
            'latest_event_identifier': payload.get('latest_event_identifier'),
        }
        if (delta := payload.get('delta')) is not None and (
            observed := payload.get('observed_balance')
        ) is not None and FVal(observed) != ZERO and abs(FVal(delta)) <= abs(FVal(observed)) * RESIDUE_RELATIVE_THRESHOLD:  # noqa: E501
            explanation['hypotheses'].append({
                'code': 'decimal_residue',
                'detail': 'The difference is negligible next to the balance',
                'basis': ['delta', 'observed_balance'],
            })
        elif delta is not None and FVal(delta) > ZERO:
            explanation['hypotheses'].append({
                'code': 'missing_inflow_history',
                'detail': 'The chain holds more than the history explains',
                'basis': ['delta'],
            })
        elif delta is not None:
            explanation['hypotheses'].append({
                'code': 'missing_outflow_history_or_wrong_direction',
                'detail': 'The history explains more than the chain holds: an outflow is '
                          'missing or an event was given the wrong balance direction',
                'basis': ['delta'],
            })
        explanation['next_actions'].append(_action(
            'trace_bucket',
            'Find the events whose effects disagree with the chain',
            bucket=serialize_bucket(bucket),
        ))
    elif issue.kind == IssueKind.UNMATCHED_BRIDGE:
        payload = issue.payload
        explanation['facts'] |= {
            'direction': payload.get('direction'),
            'counterparty': payload.get('counterparty'),
            'has_bridge_metadata': 'bridge' in payload,
        }
        if (event_identifier := payload.get('event_identifier')) is not None:
            explanation['next_actions'].append(_action(
                'explain_bridge_match',
                'See every candidate counterpart and why it was rejected',
                event_identifier=event_identifier,
            ))

    if issue.state in (IssueState.DISMISSED, IssueState.RESOLVED) and issue.payload.get(
        'resolution',
    ) is not None:
        explanation['facts']['resolution'] = {
            key: value for key, value in issue.payload['resolution'].items() if key != 'note'
        }

    return explanation
