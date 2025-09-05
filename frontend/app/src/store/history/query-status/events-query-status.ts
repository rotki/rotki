import { type HistoryEventsQueryData, HistoryEventsQueryStatus } from '@/modules/messaging/types';
import { useQueryStatusStore } from '@/store/history/query-status/index';
import { millisecondsToSeconds } from '@/utils/date';

export const useEventsQueryStatusStore = defineStore('history/events-query-status', () => {
  const createKey = ({ location, name }: Pick<HistoryEventsQueryData, 'location' | 'name'>): string => location + name;

  const isStatusFinished = (item: HistoryEventsQueryData): boolean =>
    item.status === HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED;

  const { isAllFinished, queryStatus, removeQueryStatus, resetQueryStatus }
    = useQueryStatusStore<HistoryEventsQueryData>(isStatusFinished, createKey);

  const initializeQueryStatus = (data: { location: string; name: string }[]): void => {
    resetQueryStatus();

    const status = { ...get(queryStatus) };
    const now = millisecondsToSeconds(Date.now());
    for (const item of data) {
      const key = createKey(item);
      status[key] = {
        eventType: '',
        location: item.location,
        name: item.name,
        period: [0, now],
        status: HistoryEventsQueryStatus.QUERYING_EVENTS_STARTED,
      };
    }
    set(queryStatus, status);
  };

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
    initializeQueryStatus,
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
