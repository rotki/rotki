import type { ComputedRef } from 'vue';
import { useSectionStatus } from '@/composables/status';
import { Section } from '@/modules/common/status';
import { TaskType } from '@/modules/tasks/task-type';
import { useTaskStore } from '@/modules/tasks/use-task-store';
import { useEventsQueryStatusStore } from '@/store/history/query-status/events-query-status';
import { useTxQueryStatusStore } from '@/store/history/query-status/tx-query-status';

interface UseHistoryEventStatusReturn {
  ethBlockEventsDecoding: ComputedRef<boolean>;
  anyEventsDecoding: ComputedRef<boolean>;
  txEventsDecoding: ComputedRef<boolean>;
  processing: ComputedRef<boolean>;
  refreshing: ComputedRef<boolean>;
  sectionLoading: ComputedRef<boolean>;
  isRepulling: ComputedRef<boolean>;
  shouldFetchEventsRegularly: ComputedRef<boolean>;
}

export const useHistoryEventsStatus = createSharedComposable((): UseHistoryEventStatusReturn => {
  const { useIsTaskRunning } = useTaskStore();
  const { isLoading: sectionLoading } = useSectionStatus(Section.HISTORY);

  const { isAllFinished: isQueryingTxsFinished } = storeToRefs(useTxQueryStatusStore());
  const { isAllFinished: isQueryingOnlineEventsFinished } = storeToRefs(useEventsQueryStatusStore());
  const txEventsDecoding = useIsTaskRunning(TaskType.TRANSACTIONS_DECODING);
  const ethBlockEventsDecoding = useIsTaskRunning(TaskType.ETH_BLOCK_EVENTS_DECODING);
  const anyEventsDecoding = logicOr(txEventsDecoding, ethBlockEventsDecoding);
  const protocolCacheUpdatesLoading = useIsTaskRunning(TaskType.REFRESH_GENERAL_CACHE);
  const onlineHistoryEventsLoading = useIsTaskRunning(TaskType.QUERY_ONLINE_EVENTS);
  const queryExchangeEventsLoading = useIsTaskRunning(TaskType.QUERY_EXCHANGE_EVENTS);
  const isRepulling = useIsTaskRunning(TaskType.REPULLING_TXS);
  const isTransactionsLoading = useIsTaskRunning(TaskType.TX);

  const refreshing = logicOr(sectionLoading, anyEventsDecoding, queryExchangeEventsLoading, onlineHistoryEventsLoading, protocolCacheUpdatesLoading);
  const querying = logicNot(logicOr(isQueryingTxsFinished, isQueryingOnlineEventsFinished));
  const shouldFetchEventsRegularly = logicOr(querying, refreshing);
  const processing = logicOr(isTransactionsLoading, isRepulling, refreshing);

  return {
    anyEventsDecoding,
    ethBlockEventsDecoding,
    isRepulling,
    processing,
    refreshing,
    sectionLoading,
    shouldFetchEventsRegularly,
    txEventsDecoding,
  };
});
