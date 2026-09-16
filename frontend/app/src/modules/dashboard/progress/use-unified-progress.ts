import type { ComputedRef, Ref } from 'vue';
import type { TransactionStatus } from '@/modules/history/api/events/use-history-events-api';
import { get, isDefined, set } from '@vueuse/shared';
import { useLoggedUserIdentifier } from '@/modules/auth/use-logged-user-identifier';
import { useHistoryQueryIndicatorSettings } from '@/modules/dashboard/progress/use-history-query-indicator-settings';
import { useTransactionStatusCheck } from '@/modules/dashboard/progress/use-transaction-status-check';
import { useHistoryStore } from '@/modules/history/use-history-store';

const HUNDRED_EIGHTY_DAYS = 15_552_000_000;

interface UseUnifiedProgressReturn {
  dismissalThresholdMs: Readonly<Ref<number, number>>;
  hasTxAccounts: ComputedRef<boolean>;
  isNeverQueried: ComputedRef<boolean>;
  lastQueriedDisplay: ComputedRef<string>;
  lastQueriedTimestamp: ComputedRef<number>;
  longQuery: ComputedRef<boolean>;
  minOutOfSyncPeriodMs: Readonly<Ref<number, number>>;
  processing: Ref<boolean>;
  resetQueryStatus: () => void;
  showIdleMessage: ComputedRef<boolean>;
  transactionStatusSummary: Ref<TransactionStatus | undefined>;
  queryStatus: Ref<QueryStatusDismissal>;
  navigateToHistory: () => Promise<void>;
  hasUndecodedTransactions: ComputedRef<boolean>;
}

interface QueryStatusDismissal {
  lastDismissedTs: number;
  lastUsedVersion: string | null;
}

/**
 * The dashboard's history status: whether history is out of sync, when it was last queried, and
 * whether the indicator was dismissed recently.
 *
 * @remarks
 * Progress for work in flight is the task dock's; this only says what state history was left in.
 */
export function useUnifiedProgress(): UseUnifiedProgressReturn {
  const userId = useLoggedUserIdentifier();

  const queryStatus = useLocalStorage<QueryStatusDismissal>(`${get(userId)}.rotki_query_status`, {
    lastDismissedTs: 0,
    lastUsedVersion: null,
  });

  const {
    earliestQueriedTimestamp: lastQueriedTimestamp,
    hasTxAccounts,
    isNeverQueried,
    isOutOfSync: isOutOfSyncCheck,
    navigateToHistory,
    processing,
  } = useTransactionStatusCheck();

  const { dismissalThresholdMs, minOutOfSyncPeriodMs } = useHistoryQueryIndicatorSettings();

  const historyStore = useHistoryStore();
  const { transactionStatusSummary } = storeToRefs(historyStore);
  const lastQueriedDisplay = useTimeAgo(lastQueriedTimestamp);

  const showIdleMessage = computed<boolean>(() => {
    if (!get(hasTxAccounts)) {
      return false;
    }

    return get(isOutOfSyncCheck);
  });

  const longQuery = computed<boolean>(() => {
    if (!get(hasTxAccounts)) {
      return false;
    }

    const status = get(transactionStatusSummary);
    const now = Date.now();
    const lastQueried = get(lastQueriedTimestamp);
    return isDefined(status) && status.undecodedTxCount === 0 && now - lastQueried > HUNDRED_EIGHTY_DAYS;
  });

  const hasUndecodedTransactions = computed<boolean>(() => {
    const status = get(transactionStatusSummary);

    return !!status && status.undecodedTxCount > 0;
  });

  const resetQueryStatus = (): void => {
    set(queryStatus, {
      lastDismissedTs: 0,
      lastUsedVersion: null,
    });
  };

  return {
    dismissalThresholdMs,
    hasTxAccounts,
    hasUndecodedTransactions,
    isNeverQueried,
    lastQueriedDisplay,
    lastQueriedTimestamp,
    longQuery,
    minOutOfSyncPeriodMs,
    navigateToHistory,
    processing,
    queryStatus,
    resetQueryStatus,
    showIdleMessage,
    transactionStatusSummary,
  };
}
