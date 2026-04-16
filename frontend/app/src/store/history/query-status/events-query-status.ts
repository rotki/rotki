import { millisecondsToSeconds } from '@/modules/common/data/date';
import { type HistoryEventsQueryData, HistoryEventsQueryStatus } from '@/modules/messaging/types';
import { createQueryStatusState } from '@/store/history/query-status/index';

export const useEventsQueryStatusStore = defineStore('history/events-query-status', () => {
  const createKey = ({ location, name }: Pick<HistoryEventsQueryData, 'location' | 'name'>): string => location + name;

  const isStatusFinished = (item: HistoryEventsQueryData): boolean =>
    item.status === HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED
    || item.status === HistoryEventsQueryStatus.CANCELLED;

  const { isAllFinished, markCancelled, queryStatus, removeQueryStatus, resetQueryStatus, stopSyncing, syncing }
    = createQueryStatusState<HistoryEventsQueryData>(isStatusFinished, createKey);

  const initializeQueryStatus = (data: { location: string; name: string }[]): void => {
    resetQueryStatus();
    set(syncing, true);

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
    if (!get(syncing))
      return;

    const status = { ...get(queryStatus) };
    const key = createKey(data);

    // Guard: don't overwrite cancelled entries
    if (status[key]?.status === HistoryEventsQueryStatus.CANCELLED)
      return;

    status[key] = {
      ...status[key],
      ...data,
    };
    set(queryStatus, status);
  };

  const markLocationCancelled = ({ location, name }: Pick<HistoryEventsQueryData, 'location' | 'name'>): void => {
    const key = createKey({ location, name });
    const existing = get(queryStatus)[key];
    if (existing) {
      markCancelled(key, { ...existing, status: HistoryEventsQueryStatus.CANCELLED });
    }
  };

  return {
    initializeQueryStatus,
    isAllFinished,
    isStatusFinished,
    markLocationCancelled,
    queryStatus,
    removeQueryStatus,
    resetQueryStatus,
    setQueryStatus,
    stopSyncing,
    syncing,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useEventsQueryStatusStore, import.meta.hot));
