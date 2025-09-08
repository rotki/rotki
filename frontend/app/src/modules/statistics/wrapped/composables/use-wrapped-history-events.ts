import type { ComputedRef, Ref } from 'vue';
import { get, set } from '@vueuse/shared';
import { useHistoryEvents } from '@/composables/history/events';
import { useStatusUpdater } from '@/composables/status';
import { useTaskStore } from '@/store/tasks';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';

interface UseWrappedHistoryEventsReturn {
  historyEventsReady: ComputedRef<boolean>;
  initializeStartFromEarliestEvent: () => Promise<void>;
  isFirstLoad: () => boolean;
  refreshing: ComputedRef<boolean>;
  usedHistoryEventsReady: ComputedRef<boolean>;
}

export function useWrappedHistoryEvents(start: Ref<number>): UseWrappedHistoryEventsReturn {
  const { getEarliestEventTimestamp } = useHistoryEvents();
  const { isFirstLoad, loading: sectionLoading } = useStatusUpdater(Section.HISTORY);
  const { useIsTaskRunning } = useTaskStore();

  const eventTaskLoading = useIsTaskRunning(TaskType.TRANSACTIONS_DECODING);
  const protocolCacheUpdatesLoading = useIsTaskRunning(TaskType.REFRESH_GENERAL_CACHE);
  const onlineHistoryEventsLoading = useIsTaskRunning(TaskType.QUERY_ONLINE_EVENTS);

  const refreshing = logicOr(
    sectionLoading,
    eventTaskLoading,
    onlineHistoryEventsLoading,
    protocolCacheUpdatesLoading,
  );

  const historyEventsReady = logicAnd(!isFirstLoad(), logicNot(refreshing));
  const debouncedHistoryEventsReady = debouncedRef(historyEventsReady, 500);
  const usedHistoryEventsReady = logicAnd(historyEventsReady, debouncedHistoryEventsReady);

  async function initializeStartFromEarliestEvent(): Promise<void> {
    const earliestEventTimestamp = await getEarliestEventTimestamp();
    if (earliestEventTimestamp) {
      set(start, earliestEventTimestamp);
    }
  }

  watchImmediate(usedHistoryEventsReady, async (curr, old) => {
    if (curr && !old && get(start) === 0) {
      await initializeStartFromEarliestEvent();
    }
  });

  return {
    historyEventsReady,
    initializeStartFromEarliestEvent,
    isFirstLoad,
    refreshing,
    usedHistoryEventsReady,
  };
}
