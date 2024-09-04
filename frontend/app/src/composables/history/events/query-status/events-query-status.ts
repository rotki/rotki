import type { MaybeRef } from '@vueuse/core';
import type { HistoryEventsQueryData } from '@/types/websocket-messages';

type QueryTranslationKey = 'transactions.query_status_events.done_date_range'
  | 'transactions.query_status_events.done_end_date'
  | 'transactions.query_status_events.date_range'
  | 'transactions.query_status_events.end_date';

interface UseEventsQueryStatusReturn {
  getItemTranslationKey: (item: HistoryEventsQueryData) => QueryTranslationKey;
  isQueryFinished: (item: HistoryEventsQueryData) => boolean;
  getKey: (item: HistoryEventsQueryData) => string;
  resetQueryStatus: () => void;
  isAllFinished: ComputedRef<boolean>;
  sortedQueryStatus: Ref<HistoryEventsQueryData[]>;
  filtered: ComputedRef<HistoryEventsQueryData[]>;
  queryingLength: ComputedRef<number>;
  length: ComputedRef<number>;
}

export function useEventsQueryStatus(locations: MaybeRef<string[]> = []): UseEventsQueryStatusReturn {
  const store = useEventsQueryStatusStore();
  const { isStatusFinished, resetQueryStatus } = store;
  const { queryStatus, isAllFinished } = storeToRefs(store);

  const filtered = computed<HistoryEventsQueryData[]>(() => {
    const statuses = Object.values(get(queryStatus));
    const locationsVal = get(locations);
    if (locationsVal.length === 0)
      return statuses;

    return statuses.filter(({ location }) => locationsVal.includes(location));
  });

  const { sortedQueryStatus, queryingLength, length, isQueryStatusRange } = useQueryStatus(filtered, isStatusFinished);

  const getItemTranslationKey = (item: HistoryEventsQueryData): QueryTranslationKey => {
    const isRange = isQueryStatusRange(item);

    if (isStatusFinished(item)) {
      return isRange
        ? 'transactions.query_status_events.done_date_range'
        : 'transactions.query_status_events.done_end_date';
    }

    return isRange ? 'transactions.query_status_events.date_range' : 'transactions.query_status_events.end_date';
  };

  const getKey = (item: HistoryEventsQueryData): string => item.location + item.name;

  const isQueryFinished = (item: HistoryEventsQueryData): boolean => isStatusFinished(item);

  return {
    getItemTranslationKey,
    isQueryFinished,
    getKey,
    resetQueryStatus,
    isAllFinished,
    sortedQueryStatus,
    filtered,
    queryingLength,
    length,
  };
}
