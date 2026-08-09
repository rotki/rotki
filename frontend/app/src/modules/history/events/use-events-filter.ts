import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import type { FilterSchema } from '@/modules/core/table/pagination-filter-types';
import { FilterKeyArities, filterRouteSchema } from '@/modules/core/table/route';

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
    // The backend takes entry types as `{ behaviour, values }` so a type can be excluded. The pill
    // writes exclusion as a `!` prefix, which is what the URL carries too; the wrapping happens at
    // request assembly.
    behaviourKeys: [HistoryEventFilterKeys.ENTRY_TYPE],
    filters: modelFilters,
    RouteFilterSchema: filterRouteSchema({
      [HistoryEventFilterKeys.ADDRESSES]: FilterKeyArities.MANY,
      [HistoryEventFilterKeys.ASSET]: FilterKeyArities.ONE,
      [HistoryEventFilterKeys.END]: FilterKeyArities.ONE,
      [HistoryEventFilterKeys.ENTRY_TYPE]: FilterKeyArities.MANY,
      [HistoryEventFilterKeys.EVENT_SUBTYPE]: FilterKeyArities.MANY,
      [HistoryEventFilterKeys.EVENT_TYPE]: FilterKeyArities.MANY,
      [HistoryEventFilterKeys.LOCATION]: FilterKeyArities.ONE,
      [HistoryEventFilterKeys.MAX_AMOUNT]: FilterKeyArities.ONE,
      [HistoryEventFilterKeys.MIN_AMOUNT]: FilterKeyArities.ONE,
      [HistoryEventFilterKeys.NOTES]: FilterKeyArities.ONE,
      [HistoryEventFilterKeys.PROTOCOL]: FilterKeyArities.MANY,
      [HistoryEventFilterKeys.START]: FilterKeyArities.ONE,
      [HistoryEventFilterKeys.TX_HASHES]: FilterKeyArities.MANY,
      [HistoryEventFilterKeys.VALIDATOR_INDICES]: FilterKeyArities.MANY,
    }),
  };
}
