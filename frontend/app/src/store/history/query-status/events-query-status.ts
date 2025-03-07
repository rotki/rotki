import { useQueryStatusStore } from '@/store/history/query-status/index';
import { type HistoryEventsQueryData, HistoryEventsQueryStatus } from '@/types/websocket-messages';

export const useEventsQueryStatusStore = defineStore('history/events-query-status', () => {
  const createKey = ({ location, name }: HistoryEventsQueryData): string => location + name;

  const isStatusFinished = (item: HistoryEventsQueryData): boolean =>
    item.status === HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED;

  const { isAllFinished, queryStatus, removeQueryStatus, resetQueryStatus }
    = useQueryStatusStore<HistoryEventsQueryData>(isStatusFinished, createKey);

  const setQueryStatus = (data: HistoryEventsQueryData): void => {
    const status = { ...get(queryStatus) };
    const key = createKey(data);

    status[key] = {
      ...status[key],
      ...data,
    };
    set(queryStatus, status);
  };

  return {
    isAllFinished,
    isStatusFinished,
    queryStatus,
    removeQueryStatus,
    resetQueryStatus,
    setQueryStatus,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useEventsQueryStatusStore, import.meta.hot));
