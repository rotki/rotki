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
  // Decoding runs native (Phase 2): tx decoding aggregates across every per-chain activity,
  // block-event decoding is its own kind so each can gate independently.
  const txEventsDecoding = useIsActive(ActivityKind.TX_DECODING);
  const ethBlockEventsDecoding = useIsActive(ActivityKind.ETH_BLOCK_DECODING);
  const anyEventsDecoding = logicOr(txEventsDecoding, ethBlockEventsDecoding);
  // Protocol cache refresh runs native (W9).
  const protocolCacheUpdatesLoading = useIsActive(ActivityKind.PROTOCOL_CACHE);
  // Online events run native (W7): aggregate liveness across every per-queryType activity.
  const onlineHistoryEventsLoading = useIsActivePrefix(ActivityKind.ONLINE_EVENTS);
  // Exchange events run native (Phase 2): aggregate liveness across every {location, name} activity.
  const queryExchangeEventsLoading = useIsActive(ActivityKind.EXCHANGE_EVENTS);
  // Repulling runs native (W7): a single-in-flight activity.
  const isRepulling = useIsActive(ActivityKind.REPULLING);
  // Transaction sync runs native (Phase 2): aggregate liveness across every {chain, address} activity.
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
