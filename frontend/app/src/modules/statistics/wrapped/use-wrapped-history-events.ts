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

  // The whole history refresh is one umbrella activity: its liveness is "a refresh is running",
  // its freshness is "history has loaded at least once".
  const historySyncStatus = useWorkStatus(ActivityKind.HISTORY_SYNC);
  const sectionLoading = computed<boolean>(() => get(historySyncStatus).active);
  const isFirstLoad = (): boolean => !get(historySyncStatus).everCompleted;

  // Transaction decoding runs native (Phase 2): aggregate liveness across every per-chain activity.
  const eventTaskLoading = useIsActive(ActivityKind.TX_DECODING);
  // Protocol cache refresh runs native (W9).
  const protocolCacheUpdatesLoading = useIsActive(ActivityKind.PROTOCOL_CACHE);
  // Online events run native (W7): aggregate liveness across every per-queryType activity.
  const onlineHistoryEventsLoading = useIsActivePrefix(ActivityKind.ONLINE_EVENTS);

  const refreshing = logicOr(
    sectionLoading,
    eventTaskLoading,
    onlineHistoryEventsLoading,
    protocolCacheUpdatesLoading,
  );

  // `!isFirstLoad()` used to be evaluated once, at setup, so this never became ready if history
  // had not loaded by then.
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
