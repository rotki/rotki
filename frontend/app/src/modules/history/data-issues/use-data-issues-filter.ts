import type { MatchedKeyword } from '@/modules/core/table/filtering';
import type { FilterSchema } from '@/modules/core/table/pagination-filter-types';
import { FilterKeyArities, filterRouteSchema } from '@/modules/core/table/route';

/** The wire keys the data issues table filters on, which the URL carries too. */
export const DataIssuesFilterKeys = {
  ACCOUNT: 'locationLabel',
  ASSET: 'asset',
  END: 'toTimestamp',
  KIND: 'kind',
  START: 'fromTimestamp',
  STATE: 'state',
} as const;

export type DataIssuesFilterKey = typeof DataIssuesFilterKeys[keyof typeof DataIssuesFilterKeys];

export type Filters = MatchedKeyword<DataIssuesFilterKey>;

export function useDataIssuesFilter(): FilterSchema<Filters> {
  const modelFilters = ref<Filters>({});

  return {
    filters: modelFilters,
    RouteFilterSchema: filterRouteSchema({
      [DataIssuesFilterKeys.ACCOUNT]: FilterKeyArities.ONE,
      [DataIssuesFilterKeys.ASSET]: FilterKeyArities.ONE,
      [DataIssuesFilterKeys.END]: FilterKeyArities.ONE,
      [DataIssuesFilterKeys.KIND]: FilterKeyArities.MANY,
      [DataIssuesFilterKeys.START]: FilterKeyArities.ONE,
      [DataIssuesFilterKeys.STATE]: FilterKeyArities.MANY,
    }),
  };
}
