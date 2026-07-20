import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { useHistoryTransactionDecoding } from '@/modules/history/events/tx/use-history-transaction-decoding';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';

interface UseUndecodedTransactionsCountReturn {
  undecodedCount: ComputedRef<number>;
  fetchUndecodedTransactionsBreakdown: () => Promise<void>;
}

/**
 * Counts transactions that have been fetched but not yet decoded into events.
 * While history is processing the count is suppressed, since the decoding is
 * still in flight. `processing` defaults to the shared history status but can be
 * overridden by callers that already receive it (e.g. as a prop).
 */
export function useUndecodedTransactionsCount(
  processing?: MaybeRefOrGetter<boolean>,
): UseUndecodedTransactionsCountReturn {
  const { decodingStatus } = storeToRefs(useDecodingStatusStore());
  const { processing: statusProcessing } = useHistoryEventsStatus();
  const { fetchUndecodedTransactionsBreakdown } = useHistoryTransactionDecoding();

  const isProcessing = computed<boolean>(() =>
    processing === undefined ? get(statusProcessing) : toValue(processing),
  );

  const undecodedCount = computed<number>(() => {
    if (get(isProcessing))
      return 0;
    return get(decodingStatus).reduce((sum, { processed, total }) => sum + Math.max(0, total - processed), 0);
  });

  return { fetchUndecodedTransactionsBreakdown, undecodedCount };
}
