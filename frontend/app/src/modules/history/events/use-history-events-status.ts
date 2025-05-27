import type { ComputedRef } from 'vue';
import { useEventsQueryStatusStore } from '@/store/history/query-status/events-query-status';
import { useTxQueryStatusStore } from '@/store/history/query-status/tx-query-status';
import { useStatusStore } from '@/store/status';
import { useTaskStore } from '@/store/tasks';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { not } from '@vueuse/math';

interface UseHistoryEventStatusReturn {
  ethBlockEventsDecoding: ComputedRef<boolean>;
  anyEventsDecoding: ComputedRef<boolean>;
  evmEventsDecoding: ComputedRef<boolean>;
  processing: ComputedRef<boolean>;
  refreshing: ComputedRef<boolean>;
  sectionLoading: ComputedRef<boolean>;
  shouldFetchEventsRegularly: ComputedRef<boolean>;
}

export function useHistoryEventsStatus(): UseHistoryEventStatusReturn {
  const { useIsTaskRunning } = useTaskStore();
  const { isLoading: isSectionLoading } = useStatusStore();

  const { isAllFinished: isQueryingTxsFinished } = toRefs(useTxQueryStatusStore());
  const { isAllFinished: isQueryingOnlineEventsFinished } = toRefs(useEventsQueryStatusStore());

  const sectionLoading = isSectionLoading(Section.HISTORY);
  const evmEventsDecoding = useIsTaskRunning(TaskType.TRANSACTIONS_DECODING);
  const ethBlockEventsDecoding = useIsTaskRunning(TaskType.ETH_BLOCK_EVENTS_DECODING);
  const anyEventsDecoding = logicOr(evmEventsDecoding, ethBlockEventsDecoding);
  const protocolCacheUpdatesLoading = useIsTaskRunning(TaskType.REFRESH_GENERAL_CACHE);
  const onlineHistoryEventsLoading = useIsTaskRunning(TaskType.QUERY_ONLINE_EVENTS);
  const isTransactionsLoading = useIsTaskRunning(TaskType.TX);

  const refreshing = logicOr(sectionLoading, anyEventsDecoding, onlineHistoryEventsLoading, protocolCacheUpdatesLoading);
  const querying = not(logicOr(isQueryingTxsFinished, isQueryingOnlineEventsFinished));
  const shouldFetchEventsRegularly = logicOr(querying, refreshing);
  const processing = logicOr(isTransactionsLoading, querying, refreshing);

  return {
    anyEventsDecoding,
    ethBlockEventsDecoding,
    evmEventsDecoding,
    processing,
    refreshing,
    sectionLoading,
    shouldFetchEventsRegularly,
  };
}
