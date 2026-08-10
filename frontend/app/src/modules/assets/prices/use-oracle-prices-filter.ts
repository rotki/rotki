import type { MatchedKeyword } from '@/modules/core/table/filtering';
import type { FilterSchema } from '@/modules/core/table/pagination-filter-types';

/** The wire keys the oracle prices table filters on, which the URL carries too. */
export const OraclePriceFilterKeys = {
  END: 'toTimestamp',
  FROM_ASSET: 'fromAsset',
  SOURCE: 'sourceType',
  START: 'fromTimestamp',
  TO_ASSET: 'toAsset',
} as const;

export type OraclePriceFilterKey = typeof OraclePriceFilterKeys[keyof typeof OraclePriceFilterKeys];

export type Filters = MatchedKeyword<OraclePriceFilterKey>;

export function useOraclePricesFilter(): FilterSchema<Filters> {
  const modelFilters = ref<Filters>({});

  return {
    filters: modelFilters,
  };
}
