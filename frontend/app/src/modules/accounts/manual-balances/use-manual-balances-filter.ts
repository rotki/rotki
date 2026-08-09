import type { MatchedKeyword } from '@/modules/core/table/filtering';
import type { FilterSchema } from '@/modules/core/table/pagination-filter-types';
import z from 'zod';
import { CommaSeparatedStringSchema, FilterKeyArities, filterRouteSchema } from '@/modules/core/table/route';

/** The wire keys the manual balances table filters on, which the URL carries too. */
export const ManualBalanceFilterKeys = {
  ASSET: 'asset',
  LABEL: 'label',
  LOCATION: 'location',
} as const;

export type ManualBalanceFilterKey = typeof ManualBalanceFilterKeys[keyof typeof ManualBalanceFilterKeys];

export type Filters = MatchedKeyword<ManualBalanceFilterKey>;

export function useManualBalanceFilter(): FilterSchema<Filters> {
  const modelFilters = ref<Filters>({});

  return {
    filters: modelFilters,
    RouteFilterSchema: filterRouteSchema({
      [ManualBalanceFilterKeys.ASSET]: FilterKeyArities.ONE,
      [ManualBalanceFilterKeys.LABEL]: FilterKeyArities.ONE,
      [ManualBalanceFilterKeys.LOCATION]: FilterKeyArities.ONE,
    }),
  };
}

export const ManualBalancesFilterSchema = z.object({
  tags: CommaSeparatedStringSchema,
});
