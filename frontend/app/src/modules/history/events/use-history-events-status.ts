import type { ComputedRef } from 'vue';
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
  /**
   * Whether the events table should keep re-reading because history work is in flight.
   *
   * @remarks
   * Read from the ledger only, which settles every activity whether or not the backend reported on
   * it. A sync that fails before sending any status frame still ends there, so the table stops
   * polling when the work does.
   */
  shouldFetchEventsRegularly: ComputedRef<boolean>;
}

export const useHistoryEventsStatus = createSharedComposable((): UseHistoryEventStatusReturn => {
  const { useIsActive, useIsActivePrefix } = useTaskCenter();
  // The whole history refresh is one umbrella activity; its liveness replaces the section's.
  const sectionLoading = useIsActive(ActivityKind.HISTORY_SYNC);

  const txEventsDecoding = useIsActive(ActivityKind.TX_DECODING);
  const ethBlockEventsDecoding = useIsActive(ActivityKind.ETH_BLOCK_DECODING);
  const anyEventsDecoding = logicOr(txEventsDecoding, ethBlockEventsDecoding);
  const protocolCacheUpdatesLoading = useIsActive(ActivityKind.PROTOCOL_CACHE);
  // Prefix, not exact: online events submit one activity per queryType.
  const onlineHistoryEventsLoading = useIsActivePrefix(ActivityKind.ONLINE_EVENTS);
  const queryExchangeEventsLoading = useIsActive(ActivityKind.EXCHANGE_EVENTS);
  const queryBankEventsLoading = useIsActive(ActivityKind.BANK_EVENTS);
  const isRepulling = useIsActive(ActivityKind.REPULLING);
  const isTransactionsLoading = useIsActive(ActivityKind.TX_SYNC);

  const refreshing = logicOr(sectionLoading, anyEventsDecoding, queryExchangeEventsLoading, queryBankEventsLoading, onlineHistoryEventsLoading, protocolCacheUpdatesLoading);
  const processing = logicOr(isTransactionsLoading, isRepulling, refreshing);
  const shouldFetchEventsRegularly = processing;

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
