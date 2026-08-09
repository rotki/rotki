import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import type { FilterSchema } from '@/modules/core/table/pagination-filter-types';

/** The wire keys the internal transaction conflicts table filters on. */
export const InternalTxConflictFilterKeys = {
  CHAIN: 'chain',
  FROM_TIMESTAMP: 'fromTimestamp',
  TO_TIMESTAMP: 'toTimestamp',
} as const;

export type InternalTxConflictFilterKey = typeof InternalTxConflictFilterKeys[keyof typeof InternalTxConflictFilterKeys];

export type Filters = MatchedKeywordWithBehaviour<InternalTxConflictFilterKey>;

export function useInternalTxConflictsFilter(): FilterSchema<Filters> {
  const modelFilters = ref<Filters>({});

  return {
    filters: modelFilters,
  };
}
