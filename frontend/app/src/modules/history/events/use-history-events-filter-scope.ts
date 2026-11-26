import type { HistoryEventEntryType } from '@rotki/common';
import type { Filters } from '@/modules/history/events/history-event-filter-keys';
import { computed, type ComputedRef, type MaybeRefOrGetter, toValue } from 'vue';
import {
  isBankTransactionEventType,
  isEvmEventType,
  isOnlineHistoryEventType,
} from '@/modules/history/event-utils';

interface UseHistoryEventsFilterScopeReturn {
  /** Which event families the view can hold, so the page knows which refresh actions apply. */
  includes: ComputedRef<{ evmEvents: boolean; onlineEvents: boolean }>;
  /** The locations the filter selects, normalized to a list. */
  locations: ComputedRef<string[]>;
}

/**
 * What the current filter and the view's entry types narrow the history events down to.
 *
 * @param filters - the active filter bag.
 * @param entryTypes - the entry types the view fixes; undefined means every type.
 */
export function useHistoryEventsFilterScope(
  filters: MaybeRefOrGetter<Filters>,
  entryTypes: MaybeRefOrGetter<HistoryEventEntryType[] | undefined>,
): UseHistoryEventsFilterScopeReturn {
  const locations = computed<string[]>(() => {
    const filteredData = toValue(filters);

    if ('location' in filteredData) {
      if (typeof filteredData.location === 'string')
        return [filteredData.location];
      else if (Array.isArray(filteredData.location))
        return filteredData.location;

      return [];
    }
    return [];
  });

  const includes = computed<{ evmEvents: boolean; onlineEvents: boolean }>(() => {
    const entryTypesValue = toValue(entryTypes);
    return {
      evmEvents: entryTypesValue ? entryTypesValue.some(type => isEvmEventType(type)) : true,
      onlineEvents: entryTypesValue ? entryTypesValue.some(type => isOnlineHistoryEventType(type) || isBankTransactionEventType(type)) : true,
    };
  });

  return {
    includes,
    locations,
  };
}
