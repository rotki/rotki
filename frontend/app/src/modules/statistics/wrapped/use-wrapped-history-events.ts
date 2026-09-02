import type { ComputedRef, Ref } from 'vue';
import { get, set } from '@vueuse/shared';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseWrappedHistoryEventsReturn {
  historyEventsReady: ComputedRef<boolean>;
  initializeStartFromEarliestEvent: () => Promise<void>;
  isFirstLoad: () => boolean;
  refreshing: ComputedRef<boolean>;
}

export function useWrappedHistoryEvents(start: Ref<number>): UseWrappedHistoryEventsReturn {
  const { getEarliestEventTimestamp } = useHistoryEvents();
  const { useIsActive, useWorkStatus, useIsActivePrefix } = useTaskCenter();
  const historySyncStatus = useWorkStatus(ActivityKind.HISTORY_SYNC);

  const sectionLoading = computed<boolean>(() => get(historySyncStatus).active);
  const isFirstLoad = (): boolean => !get(historySyncStatus).everCompleted;

  const eventTaskLoading = useIsActive(ActivityKind.TX_DECODING);
  const protocolCacheUpdatesLoading = useIsActive(ActivityKind.PROTOCOL_CACHE);
  const onlineHistoryEventsLoading = useIsActivePrefix(ActivityKind.ONLINE_EVENTS);

  const refreshing = logicOr(
    sectionLoading,
    eventTaskLoading,
    onlineHistoryEventsLoading,
    protocolCacheUpdatesLoading,
  );

  const everLoaded = computed<boolean>(() => get(historySyncStatus).everCompleted);
  const historyEventsReady = logicAnd(everLoaded, logicNot(refreshing));
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
