import type { ComputedRef, Ref } from 'vue';
import { useRefWithDebounce } from '@/composables/ref';
import { useHistoryQueryIndicatorSettings } from '@/modules/dashboard/progress/composables/use-history-query-indicator-settings';
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
  navigateToHistory: () => Promise<void>;

  /**
   * Check if any accounts exist
   */
  isAccountsExist: Ref<boolean>;
}

export function useTransactionStatusCheck(): UseTransactionStatusCheckReturn {
  const router = useRouter();
  const historyStore = useHistoryStore();
  const { transactionStatusSummary } = storeToRefs(historyStore);
  const { minOutOfSyncPeriodMs } = useHistoryQueryIndicatorSettings();
  const { processing: rawProcessing } = useHistoryEventsStatus();
  const processing = useRefWithDebounce(rawProcessing, 400);

  const isAccountsExist = computed<boolean>(() => {
    const status = get(transactionStatusSummary);
    if (!isDefined(status)) {
      return false;
    }

    const { hasEvmAccounts = false, hasExchangesAccounts = false } = status;

    return hasEvmAccounts || hasExchangesAccounts;
  });

  const earliestQueriedTimestamp = computed<number>(() => {
    if (!get(isAccountsExist)) {
      return 0;
    }
    const status = get(transactionStatusSummary)!;

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

  const isNeverQueried = computed<boolean>(() => {
    if (!get(isAccountsExist)) {
      return false;
    }

    return get(earliestQueriedTimestamp) === 0;
  });

  const isOutOfSync = computed<boolean>(() => {
    if (!get(isAccountsExist)) {
      return false;
    }

    const status = get(transactionStatusSummary)!;

    const { evmLastQueriedTs = 0, exchangesLastQueriedTs = 0, hasEvmAccounts = false, hasExchangesAccounts = false } = status;

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

    return get(isNeverQueried);
  });

  async function navigateToHistory(): Promise<void> {
    await router.push('/history');
  }

  return {
    earliestQueriedTimestamp,
    isAccountsExist,
    isNeverQueried,
    isOutOfSync,
    navigateToHistory,
    processing,
  };
}
