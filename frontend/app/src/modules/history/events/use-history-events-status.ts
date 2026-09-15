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
   * Read from the ledger only. The websocket status stores keep an entry for anything they were
   * seeded with until a frame settles it, and a sync that fails before reporting never sends one, so
   * gating on them kept the table polling after the work had ended and swallowed the settle read.
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
