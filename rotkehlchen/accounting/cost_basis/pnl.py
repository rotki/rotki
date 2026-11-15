"""Reads of the cost basis that is materialized on history events."""
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.accounting.cost_basis.lots import CostBasisDirection
from rotkehlchen.constants import ZERO
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.filtering import ALL_EVENTS_DATA_JOIN
from rotkehlchen.fval import FVal
from rotkehlchen.types import TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.db.filtering import HistoryBaseEntryFilterQuery


class RealizedPnlGroupBy(StrEnum):
    """What the realized PnL can be broken down by.

    The first four are parts of the bucket that the spend was made from. The rest are the
    period of the spend in UTC, with weeks starting on Monday.
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
    RealizedPnlGroupBy.WEEK: "strftime('%Y-W%W', cost_basis.timestamp / 1000, 'unixepoch')",
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
    groups: dict[str | None, tuple[FVal, FVal, set[int]]] = {}
    with database.conn.read_ctx() as cursor:
        stale_from_ts, last_processing_ts = database.get_static_caches(
            cursor=cursor,
            names=(
                DBCacheStatic.STALE_COST_BASIS_FROM_TS,
                DBCacheStatic.LAST_COST_BASIS_PROCESSING_TS,
            ),
        )
        method = database.get_settings(cursor).cost_basis_method.serialize()
        for group_key, realized_pnl, basis_removed, event_identifier in cursor.execute(
            f'SELECT {"NULL" if group_by is None else GROUP_KEY_SQL[group_by]}, '
            'cost_basis.realized_pnl, cost_basis.basis_removed, cost_basis.event_identifier '
            'FROM event_cost_basis AS cost_basis '
            'WHERE cost_basis.direction = ? AND cost_basis.event_identifier IN '
            f'(SELECT history_events.identifier {ALL_EVENTS_DATA_JOIN} {filters})',
            (CostBasisDirection.SPEND.value, *bindings),
        ):
            pnl, basis, events = groups.get(group_key, (ZERO, ZERO, set()))
            events.add(event_identifier)
            groups[group_key] = (pnl + FVal(realized_pnl), basis + FVal(basis_removed), events)

    return {
        'total_realized_pnl': str(sum((pnl for pnl, _, _ in groups.values()), start=ZERO)),
        'breakdown': [{
            'group_key': group_key,
            'realized_pnl': str(pnl),
            'basis_removed': str(basis),
            'num_events': len(events),
        } for group_key, (pnl, basis, events) in sorted(
            groups.items(),
            key=lambda item: item[0] or '',
        )],
        'stale': stale_from_ts is not None or last_processing_ts is None,
        'method': method,
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
