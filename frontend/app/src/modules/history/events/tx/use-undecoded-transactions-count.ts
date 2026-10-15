import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { startPromise } from '@shared/utils';
import { useHistoryTransactionDecoding } from '@/modules/history/events/tx/use-history-transaction-decoding';
import { useUndecodedTransactionsStatus } from '@/modules/history/events/tx/use-undecoded-transactions-status';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseUndecodedTransactionsCountReturn {
  undecodedCount: ComputedRef<number>;
  /** Whether transactions are being decoded right now; the task dock shows the progress by chain. */
  decoding: ComputedRef<boolean>;
  /** Decodes what is still undecoded, in the background. */
  decodeMissing: () => void;
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
  const { fetchUndecodedTransactionsBreakdown } = useUndecodedTransactionsStatus();
  const { checkMissingEventsAndRedecode } = useHistoryTransactionDecoding();
  const decoding = useTaskCenter().useIsActive(ActivityKind.TX_DECODING);

  const isProcessing = computed<boolean>(() =>
    processing === undefined ? get(statusProcessing) : toValue(processing),
  );

  const undecodedCount = computed<number>(() => {
    if (get(isProcessing))
      return 0;
    return get(decodingStatus).reduce((sum, { processed, total }) => sum + Math.max(0, total - processed), 0);
  });

  function decodeMissing(): void {
    startPromise(checkMissingEventsAndRedecode());
  }

  return { decodeMissing, decoding, fetchUndecodedTransactionsBreakdown, undecodedCount };
}
