import { type MaybeRef } from '@vueuse/core';
import { type HistoryEventsQueryData } from '@/types/websocket-messages';

export const useEventsQueryStatus = (locations: MaybeRef<string[]> = []) => {
  const store = useEventsQueryStatusStore();
  const { isStatusFinished, resetQueryStatus } = store;
  const { queryStatus, isAllFinished } = storeToRefs(store);

  const filtered: ComputedRef<HistoryEventsQueryData[]> = computed(() => {
    const statuses = Object.values(get(queryStatus));
    const locationsVal = get(locations);
    if (locationsVal.length === 0) {
      return statuses;
    }

    return statuses.filter(({ location }) => locationsVal.includes(location));
  });

  const getItemTranslationKey = (item: HistoryEventsQueryData) => {
    const isRange = isQueryStatusRange(item);

    if (isStatusFinished(item)) {
      return isRange
        ? 'transactions.query_status_events.done_date_range'
        : 'transactions.query_status_events.done_end_date';
    }

    return isRange
      ? 'transactions.query_status_events.date_range'
      : 'transactions.query_status_events.end_date';
  };

  const { sortedQueryStatus, queryingLength, length, isQueryStatusRange } =
    useQueryStatus(filtered, isStatusFinished);

  const getKey = (item: HistoryEventsQueryData) => item.location + item.name;

  const isQueryFinished = (item: HistoryEventsQueryData) =>
    isStatusFinished(item);

  return {
    getItemTranslationKey,
    isQueryFinished,
    getKey,
    resetQueryStatus,
    isAllFinished,
    sortedQueryStatus,
    filtered,
    queryingLength,
    length
  };
};
