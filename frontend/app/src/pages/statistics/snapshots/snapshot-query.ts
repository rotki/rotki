import type { TablePaginationData } from '@rotki/ui-library';
import type { LocationQueryRaw } from 'vue-router';
import type { LocationQuery } from '@/modules/core/table/route';
import type { SnapshotListFilters } from '@/modules/dashboard/snapshots/composables/use-snapshot-list';

/**
 * The date range carried by the URL query. A param that is absent, empty or not a finite number
 * reads as no bound at all rather than as `NaN`, which would filter every row away.
 */
export function parseSnapshotFilters(query: LocationQuery): SnapshotListFilters {
  const from = Number(query.from);
  const to = Number(query.to);
  return {
    fromTimestamp: query.from && Number.isFinite(from) ? from : undefined,
    toTimestamp: query.to && Number.isFinite(to) ? to : undefined,
  };
}

/**
 * The view-state as a URL query. Anything at its default is left out, so the common case is a bare
 * `/statistics/snapshots` rather than a URL restating every default.
 */
export function toSnapshotQuery(
  filters: SnapshotListFilters,
  pagination: TablePaginationData,
  defaultLimit: number,
): LocationQueryRaw {
  const { fromTimestamp, toTimestamp } = filters;
  const { limit, page } = pagination;
  return {
    ...(fromTimestamp !== undefined ? { from: fromTimestamp } : {}),
    ...(toTimestamp !== undefined ? { to: toTimestamp } : {}),
    ...(page > 1 ? { page } : {}),
    ...(limit !== defaultLimit ? { limit } : {}),
  };
}
