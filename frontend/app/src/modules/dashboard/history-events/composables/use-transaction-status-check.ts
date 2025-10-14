import type { ComputedRef, Ref } from 'vue';
import { useRefWithDebounce } from '@/composables/ref';
import { useHistoryQueryIndicatorSettings } from '@/modules/dashboard/history-events/composables/use-history-query-indicator-settings';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useHistoryStore } from '@/store/history';

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
  navigateToHistory: () => void;
}

export function useTransactionStatusCheck(): UseTransactionStatusCheckReturn {
  const router = useRouter();
  const historyStore = useHistoryStore();
  const { transactionStatusSummary } = storeToRefs(historyStore);
  const { minOutOfSyncPeriodMs } = useHistoryQueryIndicatorSettings();
  const { processing: rawProcessing } = useHistoryEventsStatus();
  const processing = useRefWithDebounce(rawProcessing, 400);

  const earliestQueriedTimestamp = computed<number>(() => {
    const status = get(transactionStatusSummary);
    if (!isDefined(status)) {
      return 0;
    }

    const { evmLastQueriedTs = 0, exchangesLastQueriedTs = 0, hasEvmAccounts = false, hasExchangesAccounts = false } = status;

    // Only consider timestamps for account types the user has
    const timestamps: number[] = [];
    if (hasEvmAccounts && evmLastQueriedTs > 0) {
      timestamps.push(evmLastQueriedTs);
    }
    if (hasExchangesAccounts && exchangesLastQueriedTs > 0) {
      timestamps.push(exchangesLastQueriedTs);
    }

    if (timestamps.length === 0) {
      return 0;
    }

    // Use the earliest (minimum) timestamp to show the most out-of-sync status
    // Convert seconds to milliseconds
    return Math.min(...timestamps) * 1000;
  });

  const isNeverQueried = computed<boolean>(() => get(earliestQueriedTimestamp) === 0);

  const isOutOfSync = computed<boolean>(() => {
    const status = get(transactionStatusSummary);
    if (!isDefined(status)) {
      return false;
    }

    const { evmLastQueriedTs = 0, exchangesLastQueriedTs = 0, hasEvmAccounts = false, hasExchangesAccounts = false } = status;

    // Only check if user has accounts
    if (!hasEvmAccounts && !hasExchangesAccounts) {
      return false;
    }

    const now = Date.now();
    const minOutOfSyncMs = get(minOutOfSyncPeriodMs);

    // Check EVM if user has EVM accounts
    if (hasEvmAccounts && evmLastQueriedTs > 0) {
      const evmLastQueriedMs = evmLastQueriedTs * 1000;
      if (now - evmLastQueriedMs >= minOutOfSyncMs) {
        return true;
      }
    }

    // Check exchanges if user has exchange accounts
    if (hasExchangesAccounts && exchangesLastQueriedTs > 0) {
      const exchangesLastQueriedMs = exchangesLastQueriedTs * 1000;
      if (now - exchangesLastQueriedMs >= minOutOfSyncMs) {
        return true;
      }
    }

    // Also consider it out of sync if never queried
    if ((hasEvmAccounts && evmLastQueriedTs === 0) || (hasExchangesAccounts && exchangesLastQueriedTs === 0)) {
      return true;
    }

    return false;
  });

  async function navigateToHistory(): Promise<void> {
    await router.push('/history');
  }

  return {
    earliestQueriedTimestamp,
    isNeverQueried,
    isOutOfSync,
    navigateToHistory,
    processing,
  };
}
