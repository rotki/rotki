import type { ComputedRef, Ref } from 'vue';
import { get } from '@vueuse/shared';
import { useRefWithDebounce } from '@/modules/core/common/use-ref-debounce';
import { useHistoryQueryIndicatorSettings } from '@/modules/dashboard/progress/use-history-query-indicator-settings';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useHistoryStore } from '@/modules/history/use-history-store';

const SECONDS_TO_MS = 1_000;

interface UseTransactionStatusCheckReturn {
  /**
   * The earliest queried timestamp in milliseconds (minimum of EVM and exchanges).
   * Returns 0 if never queried or no accounts exist.
   */
  earliestQueriedTimestamp: ComputedRef<number>;

  /**
   * Whether any account type (EVM or exchanges) has never been queried.
   */
  isNeverQueried: ComputedRef<boolean>;

  /**
   * Whether any account type (EVM or exchanges) is out of sync based on minOutOfSyncPeriodMs.
   */
  isOutOfSync: ComputedRef<boolean>;

  /**
   * Debounced processing state for history events.
   */
  processing: Ref<boolean>;

  /**
   * Navigates to the history events page.
   */
  navigateToHistory: () => Promise<void>;

  /**
   * Check if any accounts exist
   */
  hasTxAccounts: ComputedRef<boolean>;
}

/**
 * The last-queried timestamps of the account families the user actually has and that have been queried
 * at least once, in seconds. Both families are shaped the same way, so every caller can treat them as
 * one list instead of repeating the EVM and exchange checks side by side.
 */
function queriedTimestamps(status: {
  evmLastQueriedTs?: number;
  exchangesLastQueriedTs?: number;
  hasEvmAccounts?: boolean;
  hasExchangesAccounts?: boolean;
}): number[] {
  const {
    evmLastQueriedTs = 0,
    exchangesLastQueriedTs = 0,
    hasEvmAccounts = false,
    hasExchangesAccounts = false,
  } = status;

  return [
    { hasAccounts: hasEvmAccounts, lastQueriedTs: evmLastQueriedTs },
    { hasAccounts: hasExchangesAccounts, lastQueriedTs: exchangesLastQueriedTs },
  ]
    .filter(source => source.hasAccounts && source.lastQueriedTs > 0)
    .map(source => source.lastQueriedTs);
}

export function useTransactionStatusCheck(): UseTransactionStatusCheckReturn {
  const router = useRouter();
  const historyStore = useHistoryStore();
  const { transactionStatusSummary } = storeToRefs(historyStore);
  const { minOutOfSyncPeriodMs } = useHistoryQueryIndicatorSettings();
  const { processing: rawProcessing } = useHistoryEventsStatus();
  const processing = useRefWithDebounce(rawProcessing, 400);

  const hasTxAccounts = computed<boolean>(() => {
    const status = get(transactionStatusSummary);
    if (!isDefined(status)) {
      return false;
    }

    const { hasEvmAccounts = false, hasExchangesAccounts = false } = status;

    return hasEvmAccounts || hasExchangesAccounts;
  });

  const earliestQueriedTimestamp = computed<number>(() => {
    if (!get(hasTxAccounts)) {
      return 0;
    }

    const timestamps = queriedTimestamps(get(transactionStatusSummary)!);
    if (timestamps.length === 0) {
      return 0;
    }

    return Math.min(...timestamps) * SECONDS_TO_MS;
  });

  const isNeverQueried = computed<boolean>(() => {
    if (!get(hasTxAccounts)) {
      return false;
    }

    return get(earliestQueriedTimestamp) === 0;
  });

  const isOutOfSync = computed<boolean>(() => {
    if (!get(hasTxAccounts)) {
      return false;
    }

    const now = Date.now();
    const minOutOfSyncMs = get(minOutOfSyncPeriodMs);

    // Any account family left unqueried for longer than the period puts the whole status out of sync.
    const staleFamily = queriedTimestamps(get(transactionStatusSummary)!)
      .some(lastQueriedTs => now - lastQueriedTs * 1000 >= minOutOfSyncMs);

    return staleFamily || get(isNeverQueried);
  });

  async function navigateToHistory(): Promise<void> {
    await router.push({ name: '/history/events/' });
  }

  return {
    earliestQueriedTimestamp,
    hasTxAccounts,
    isNeverQueried,
    isOutOfSync,
    navigateToHistory,
    processing,
  };
}
