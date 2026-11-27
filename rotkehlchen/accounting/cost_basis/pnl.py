"""Reads of the cost basis that is materialized on history events."""
import json
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.accounting.cost_basis.lots import BasisSource, CostBasisDirection
from rotkehlchen.accounting.cost_basis.rules import CostBasisRules
from rotkehlchen.constants import ZERO
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.filtering import ALL_EVENTS_DATA_JOIN
from rotkehlchen.db.utils import get_query_chunks
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.constants import IssueState
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.types import (
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.types import TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.db.filtering import HistoryBaseEntryFilterQuery

OPEN_ISSUE_STATES: Final = (
    IssueState.OPEN.value,
    IssueState.AUTO_REMEDIATING.value,
    IssueState.UNRESOLVED.value,
)
SPECIAL_ENTRY_TYPES_WITHOUT_RULES: Final = frozenset({
    HistoryBaseEntryType.ASSET_MOVEMENT_EVENT.serialize_for_db(),
    HistoryBaseEntryType.ETH_BLOCK_EVENT.serialize_for_db(),
    HistoryBaseEntryType.ETH_DEPOSIT_EVENT.serialize_for_db(),
    HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT.serialize_for_db(),
})


def _evaluated_through_ts_ms(filter_query: HistoryBaseEntryFilterQuery) -> int | None:
    """Return the upper timestamp bound of `filter_query` in milliseconds, or None if unbounded."""
    ts_filter = filter_query.timestamp_filter
    if ts_filter.to_ts is None:
        return None
    if ts_filter.scaling_factor is not None:
        return (ts_filter.to_ts * ts_filter.scaling_factor).to_int(exact=False)
    return int(ts_filter.to_ts)


def _query_open_issues_by_kind(
        cursor: DBCursor,
        evaluated_through_ts: int | None,
) -> dict[str, int]:
    """Count open/unresolved/auto-remediating issues with `ts_start <= evaluated_through_ts`."""
    query = 'SELECT kind, COUNT(*) FROM data_issues WHERE state IN (?, ?, ?)'
    bindings: list[Any] = [*OPEN_ISSUE_STATES]
    if evaluated_through_ts is not None:
        query += ' AND ts_start <= ?'
        bindings.append(evaluated_through_ts)
    query += ' GROUP BY kind ORDER BY kind'
    return {
        kind: count
        for kind, count in cursor.execute(query, bindings)
        if count > 0
    }


def _count_unruled_events(
        cursor: DBCursor,
        database: DBHandler,
        filters: str,
        bindings: list[Any],
) -> int:
    """Count distinct lot-affecting events matching `filters` that have no accounting rule.

    Excludes internal transfers (both `TRANSFER` events and dual-bucket / `transfer_in`
    carryover rows), asset movements, ETH2 staking events, and swap/basis-transfer companion
    legs whose group already carries a treatment rule on its spend leg.
    """
    rules = CostBasisRules(database=database, cursor=cursor)
    event_rows: dict[int, tuple[str, str, str, int, str | None, set[str], set[str | None]]] = {}
    for (
        event_id,
        group_id,
        event_type_raw,
        event_subtype_raw,
        entry_type_raw,
        counterparty,
        direction,
        basis_source,
    ) in cursor.execute(
        'SELECT cost_basis.event_identifier, he.group_identifier, he.type, he.subtype, '
        'he.entry_type, cei.counterparty, cost_basis.direction, cost_basis.basis_source '
        'FROM event_cost_basis AS cost_basis '
        'JOIN history_events AS he ON he.identifier = cost_basis.event_identifier '
        'LEFT JOIN chain_events_info AS cei ON cei.identifier = he.identifier '
        'WHERE cost_basis.event_identifier IN '
        '(SELECT history_events.identifier AS history_events_identifier '
        f'{ALL_EVENTS_DATA_JOIN} {filters})',
        bindings,
    ):
        entry = event_rows.get(event_id)
        if entry is None:
            event_rows[event_id] = (
                group_id,
                event_type_raw,
                event_subtype_raw,
                entry_type_raw,
                counterparty,
                {direction},
                {basis_source},
            )
        else:
            entry[5].add(direction)
            entry[6].add(basis_source)

    if len(event_rows) == 0:
        return 0

    ruled_groups: set[str] = set()
    candidate_unruled: list[tuple[int, str]] = []
    for (
        event_id,
        (group_id, event_type_raw, event_subtype_raw, entry_type_raw, counterparty, dirs, sources),
    ) in event_rows.items():
        try:
            event_type = HistoryEventType.deserialize(event_type_raw)
            event_subtype = HistoryEventSubType.deserialize(event_subtype_raw)
        except ValueError:
            continue
        rule = rules.get_for_fields(
            event_identifier=event_id,
            event_type=event_type,
            event_subtype=event_subtype,
            counterparty=counterparty,
        )
        if rule is not None and rule.accounting_treatment is not None:
            ruled_groups.add(group_id)
        if (
            rule is not None or
            entry_type_raw in SPECIAL_ENTRY_TYPES_WITHOUT_RULES or
            event_type in {HistoryEventType.TRANSFER, HistoryEventType.EXCHANGE_TRANSFER} or
            len(dirs) > 1 or
            BasisSource.TRANSFER_IN.value in sources
        ):
            continue
        candidate_unruled.append((event_id, group_id))

    if len(candidate_unruled) == 0:
        return 0

    # A filter (e.g. by asset) can exclude a swap/basis-transfer's spend leg whose rule governs
    # the group. Inspect sibling events of candidate groups so ruled companion legs aren't
    # falsely counted as unruled.
    unresolved_groups = sorted({
        group_id for _event_id, group_id in candidate_unruled if group_id not in ruled_groups
    })
    for chunk, placeholders in get_query_chunks(data=unresolved_groups):
        for sib_id, sib_group, sib_type_raw, sib_subtype_raw, sib_cpt in cursor.execute(
            'SELECT he.identifier, he.group_identifier, he.type, he.subtype, cei.counterparty '
            'FROM history_events AS he '
            'LEFT JOIN chain_events_info AS cei ON cei.identifier = he.identifier '
            f'WHERE he.group_identifier IN ({placeholders})',
            chunk,
        ):
            if sib_group in ruled_groups:
                continue
            try:
                sib_type = HistoryEventType.deserialize(sib_type_raw)
                sib_subtype = HistoryEventSubType.deserialize(sib_subtype_raw)
            except ValueError:
                continue
            sib_rule = rules.get_for_fields(
                event_identifier=sib_id,
                event_type=sib_type,
                event_subtype=sib_subtype,
                counterparty=sib_cpt,
            )
            if sib_rule is not None and sib_rule.accounting_treatment is not None:
                ruled_groups.add(sib_group)

    return sum(1 for _event_id, group_id in candidate_unruled if group_id not in ruled_groups)


class RealizedPnlGroupBy(StrEnum):
    """What the realized PnL can be broken down by.

    The first four are parts of the bucket that the spend was made from. The rest are the
    period of the spend in UTC, using ISO 8601 weeks.
    """
    ASSET = auto()
    LOCATION = auto()
    LOCATION_LABEL = auto()
    PROTOCOL = auto()
    DAY = auto()
    WEEK = auto()
    MONTH = auto()
    YEAR = auto()


GROUP_KEY_SQL: Final = {
    RealizedPnlGroupBy.ASSET: 'cost_basis.asset',
    RealizedPnlGroupBy.LOCATION: 'cost_basis.location',
    RealizedPnlGroupBy.LOCATION_LABEL: 'cost_basis.location_label',
    RealizedPnlGroupBy.PROTOCOL: 'cost_basis.protocol',
    RealizedPnlGroupBy.DAY: "strftime('%Y-%m-%d', cost_basis.timestamp / 1000, 'unixepoch')",
    RealizedPnlGroupBy.WEEK: "strftime('%G-W%V', cost_basis.timestamp / 1000, 'unixepoch')",
    RealizedPnlGroupBy.MONTH: "strftime('%Y-%m', cost_basis.timestamp / 1000, 'unixepoch')",
    RealizedPnlGroupBy.YEAR: "strftime('%Y', cost_basis.timestamp / 1000, 'unixepoch')",
}


def query_realized_pnl(
        database: DBHandler,
        filter_query: HistoryBaseEntryFilterQuery,
        group_by: RealizedPnlGroupBy | None,
) -> dict[str, Any]:
    """Sum what the history events matching the filter realized, optionally by group.

    Nothing is computed here other than the sums, which are taken over the rows that the cost
    basis pass wrote. So the result is only as fresh as that pass, which is what `stale` says,
    and it is in the profit currency and cost basis method that the pass ran with.

    The amounts are summed here and not in SQLite, where they would be summed as floats.
    """
    filters, bindings = filter_query.prepare(with_pagination=False, with_order=False)
    evaluated_through_ts = _evaluated_through_ts_ms(filter_query)
    groups: dict[str | None, tuple[FVal, FVal, FVal, set[int], set[int]]] = {}
    all_unpriced_events: set[int] = set()
    with database.conn.read_ctx() as cursor:
        stale_from_ts, last_processing_ts = database.get_static_caches(
            cursor=cursor,
            names=(
                DBCacheStatic.STALE_COST_BASIS_FROM_TS,
                DBCacheStatic.LAST_COST_BASIS_PROCESSING_TS,
            ),
        )
        method = database.get_settings(cursor).cost_basis_method.serialize()
        for group_key, realized_pnl, taxfree_pnl, basis_removed, event_identifier in cursor.execute(  # noqa: E501
            f'SELECT {"NULL" if group_by is None else GROUP_KEY_SQL[group_by]}, '
            'cost_basis.realized_pnl, cost_basis.taxfree_pnl, cost_basis.basis_removed, '
            'cost_basis.event_identifier '
            'FROM event_cost_basis AS cost_basis '
            'WHERE (cost_basis.direction = ? '
            'OR (cost_basis.direction = ? AND cost_basis.is_taxable = 1)) '
            'AND cost_basis.event_identifier IN '
            '(SELECT history_events.identifier AS history_events_identifier '
            f'{ALL_EVENTS_DATA_JOIN} {filters})',
            (CostBasisDirection.SPEND.value, CostBasisDirection.RECEIVE.value, *bindings),
        ):
            pnl, taxfree, basis, events, unpriced_events = groups.get(
                group_key,
                (ZERO, ZERO, ZERO, set(), set()),
            )
            events.add(event_identifier)
            if realized_pnl is None:
                unpriced_events.add(event_identifier)
                all_unpriced_events.add(event_identifier)
            else:
                pnl += FVal(realized_pnl)
                if taxfree_pnl is not None:
                    taxfree += FVal(taxfree_pnl)
            groups[group_key] = (
                pnl,
                taxfree,
                basis + (FVal(basis_removed) if basis_removed is not None else ZERO),
                events,
                unpriced_events,
            )

        open_issues_by_kind = _query_open_issues_by_kind(
            cursor=cursor,
            evaluated_through_ts=evaluated_through_ts,
        )
        num_unruled_events = _count_unruled_events(
            cursor=cursor,
            database=database,
            filters=filters,
            bindings=bindings,
        )

    stale = stale_from_ts is not None or last_processing_ts is None
    open_issues_count = sum(open_issues_by_kind.values())
    num_unpriced_events = len(all_unpriced_events)
    return {
        'total_realized_pnl': str(sum((pnl for pnl, _, _, _, _ in groups.values()), start=ZERO)),
        'total_taxfree_pnl': str(sum((taxfree for _, taxfree, _, _, _ in groups.values()), start=ZERO)),  # noqa: E501
        'num_unpriced_events': num_unpriced_events,
        'num_unruled_events': num_unruled_events,
        'breakdown': [{
            'group_key': group_key,
            'realized_pnl': str(pnl),
            'taxfree_pnl': str(taxfree),
            'basis_removed': str(basis),
            'num_events': len(events),
            'num_unpriced_events': len(unpriced_events),
        } for group_key, (pnl, taxfree, basis, events, unpriced_events) in sorted(
            groups.items(),
            key=lambda item: item[0] or '',
        )],
        'stale': stale,
        'method': method,
        'report_readiness': {
            'ready': (not stale) and open_issues_count == 0,
            'stale': stale,
            'open_issues_count': open_issues_count,
            'open_issues_by_kind': open_issues_by_kind,
            'num_unpriced_events': num_unpriced_events,
            'num_unruled_events': num_unruled_events,
            'evaluated_through_ts': evaluated_through_ts,
        },
    }


def get_unprocessed_from_ts(
        cursor: DBCursor,
        database: DBHandler,
) -> TimestampMS | None:
    """The timestamp from which events still need cost basis processing, or None if none do.

    Includes the progress of an unfinished pass while nothing has changed since it started.
    """
    (
        stale_from_ts,
        last_processing_ts,
        modification_ts,
        pass_processed_ts,
        pass_modification_ts,
    ) = database.get_static_caches(
        cursor=cursor,
        names=(
            DBCacheStatic.STALE_COST_BASIS_FROM_TS,
            DBCacheStatic.LAST_COST_BASIS_PROCESSING_TS,
            DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS,
            DBCacheStatic.COST_BASIS_PASS_PROCESSED_TS,
            DBCacheStatic.COST_BASIS_PASS_MODIFICATION_TS,
        ),
    )
    unprocessed_from_ts = (
        0 if last_processing_ts is None
        else None if stale_from_ts is None
        else int(stale_from_ts)
    )
    if (
        unprocessed_from_ts is not None and
        pass_processed_ts is not None and
        pass_modification_ts == (modification_ts or '0')
    ):
        unprocessed_from_ts = max(unprocessed_from_ts, int(pass_processed_ts))

    return None if unprocessed_from_ts is None else TimestampMS(unprocessed_from_ts)


def query_events_cost_basis(
        database: DBHandler,
        event_identifiers: list[int],
) -> dict[str, Any]:
    """Return what the cost basis pass materialized for each of the given history events.

    An event has one entry per bucket and direction it affected, so a transfer between two
    accounts has two, and events that do not affect any lots have none and are left out. Events
    at or after the stale marker are waiting to be calculated, so their identifiers are returned
    in `stale` instead of their entries. That excludes the events a pass that has not finished
    already wrote the rows of, as long as nothing changed since it started.

    Each lot a spend consumed comes with the history event that acquired it, if that event
    still exists. That is the original acquisition also for lots that have since moved between
    accounts. A lot named after a transfer is what arrived with no known history.
    """
    entries: dict[str, list[dict[str, Any]]] = {}
    lots: list[dict[str, Any]] = []
    stale: list[int] = []
    with database.conn.read_ctx() as cursor:
        method = database.get_settings(cursor).cost_basis_method.serialize()
        unprocessed_from_ts = get_unprocessed_from_ts(cursor=cursor, database=database)
        for chunk, placeholders in get_query_chunks(data=event_identifiers):
            if unprocessed_from_ts is not None:
                stale.extend(
                    identifier for (identifier,) in cursor.execute(
                        'SELECT identifier FROM history_events '
                        f'WHERE identifier IN ({placeholders}) AND timestamp >= ? '
                        'ORDER BY identifier',
                        (*chunk, unprocessed_from_ts),
                    )
                )
                if unprocessed_from_ts <= 0:
                    continue

            timestamp_filter = '' if unprocessed_from_ts is None else ' AND timestamp < ?'
            bindings = chunk if unprocessed_from_ts is None else [*chunk, unprocessed_from_ts]
            for row in cursor.execute(
                'SELECT event_identifier, direction, location, location_label, protocol, asset, '
                'method, lot_created_id, basis_per_unit, basis_source, lots_consumed_json, '
                'proceeds, realized_pnl, taxfree_pnl, basis_removed, post_spend_basis_remaining '
                f'FROM event_cost_basis WHERE event_identifier IN ({placeholders})'
                f'{timestamp_filter} ORDER BY timestamp, sequence_index, id',
                bindings,
            ):
                entry: dict[str, Any] = {
                    'direction': row[1],
                    'location': row[2],
                    'location_label': row[3],
                    'protocol': row[4],
                    'asset': row[5],
                    'method': row[6],
                }
                if row[1] == CostBasisDirection.RECEIVE.value:
                    entry |= {
                        'lot_ids': row[7].split(',') if row[7] else [],
                        'basis_per_unit': row[8],
                        'basis_source': row[9],
                    }
                else:
                    entry |= {
                        'lots': (consumed_lots := [{
                            'lot_id': lot['lot_id'],
                            'acquired_at': lot['acquired_at'],
                            'amount': lot['amount_consumed'],
                            'basis_per_unit': lot['basis_per_unit'],
                            'taxable': lot['taxable'],
                            'acquisition': None,
                        } for lot in json.loads(row[10])]),
                        'proceeds': row[11],
                        'realized_pnl': row[12],
                        'taxfree_pnl': row[13],
                        'basis_removed': row[14],
                        'basis_remaining': row[15],
                    }
                    lots.extend(consumed_lots)

                entries.setdefault(str(row[0]), []).append(entry)

        acquisitions: dict[str, dict[str, Any]] = {}
        for chunk, placeholders in get_query_chunks(
            data=list({int(lot['lot_id']) for lot in lots}),
        ):
            acquisitions.update({str(identifier): {
                'identifier': identifier,
                'group_identifier': group_identifier,
                'location': location,
                'location_label': location_label,
                'timestamp': timestamp,
            } for identifier, group_identifier, location, location_label, timestamp in cursor.execute(  # noqa: E501
                'SELECT identifier, group_identifier, location, location_label, timestamp '
                f'FROM history_events WHERE identifier IN ({placeholders})',
                chunk,
            )})

    for lot in lots:
        lot['acquisition'] = acquisitions.get(lot['lot_id'])

    return {
        'entries': entries,
        'stale': stale,
        'method': method,
    }
