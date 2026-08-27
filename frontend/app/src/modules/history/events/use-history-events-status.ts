import type { ComputedRef } from 'vue';
import { useEventsQueryStatusStore } from '@/modules/history/use-events-query-status-store';
import { useTxQueryStatusStore } from '@/modules/history/use-tx-query-status-store';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

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
  const { useIsActive, useIsActivePrefix } = useTaskCenter();
  // The whole history refresh is one umbrella activity; its liveness replaces the section's.
  const sectionLoading = useIsActive(ActivityKind.HISTORY_SYNC);

  const { isAllFinished: isQueryingTxsFinished } = storeToRefs(useTxQueryStatusStore());
  const { isAllFinished: isQueryingOnlineEventsFinished } = storeToRefs(useEventsQueryStatusStore());
  const txEventsDecoding = useIsActive(ActivityKind.TX_DECODING);
  const ethBlockEventsDecoding = useIsActive(ActivityKind.ETH_BLOCK_DECODING);
  const anyEventsDecoding = logicOr(txEventsDecoding, ethBlockEventsDecoding);
  const protocolCacheUpdatesLoading = useIsActive(ActivityKind.PROTOCOL_CACHE);
  // Prefix, not exact: online events submit one activity per queryType.
  const onlineHistoryEventsLoading = useIsActivePrefix(ActivityKind.ONLINE_EVENTS);
  const queryExchangeEventsLoading = useIsActive(ActivityKind.EXCHANGE_EVENTS);
  const isRepulling = useIsActive(ActivityKind.REPULLING);
  const isTransactionsLoading = useIsActive(ActivityKind.TX_SYNC);

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
