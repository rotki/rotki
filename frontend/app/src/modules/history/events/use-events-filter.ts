import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import type { FilterSchema } from '@/modules/core/table/pagination-filter-types';

/** The wire keys the history events table filters on, which the URL carries too. */
export const HistoryEventFilterKeys = {
  ADDRESSES: 'addresses',
  ASSET: 'asset',
  END: 'toTimestamp',
  ENTRY_TYPE: 'entryTypes',
  EVENT_SUBTYPE: 'eventSubtypes',
  EVENT_TYPE: 'eventTypes',
  LOCATION: 'location',
  MAX_AMOUNT: 'maxAmount',
  MIN_AMOUNT: 'minAmount',
  NOTES: 'notesSubstring',
  PROTOCOL: 'counterparties',
  START: 'fromTimestamp',
  TX_HASHES: 'txRefs',
  VALIDATOR_INDICES: 'validatorIndices',
} as const;

export type HistoryEventFilterKey = typeof HistoryEventFilterKeys[keyof typeof HistoryEventFilterKeys];

export type Filters = MatchedKeywordWithBehaviour<HistoryEventFilterKey>;

export function useHistoryEventFilter(): FilterSchema<Filters> {
  const modelFilters = ref<Filters>({});

  return {
    filters: modelFilters,
  };
}
