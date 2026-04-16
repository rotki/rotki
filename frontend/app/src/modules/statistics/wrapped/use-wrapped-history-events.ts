import type { ComputedRef, Ref } from 'vue';
import { get, set } from '@vueuse/shared';
import { Section } from '@/modules/core/common/status';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';
import { useStatusUpdater } from '@/modules/shell/sync-progress/use-status-updater';

interface UseWrappedHistoryEventsReturn {
  historyEventsReady: ComputedRef<boolean>;
  initializeStartFromEarliestEvent: () => Promise<void>;
  isFirstLoad: () => boolean;
  refreshing: ComputedRef<boolean>;
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
  const usedHistoryEventsReady = refDebounced(historyEventsReady, 500);

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
  };
}
