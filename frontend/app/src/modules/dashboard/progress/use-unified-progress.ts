import type { ComputedRef, Ref } from 'vue';
import type { TransactionStatus } from '@/modules/history/api/events/use-history-events-api';
import { get, isDefined, set } from '@vueuse/shared';
import { useLoggedUserIdentifier } from '@/modules/auth/use-logged-user-identifier';
import { type BalanceQueryProgress, useBalanceQueryProgress } from '@/modules/dashboard/progress/use-balance-query-progress';
import { useHistoryQueryIndicatorSettings } from '@/modules/dashboard/progress/use-history-query-indicator-settings';
import { type HistoryQueryProgress, useHistoryQueryProgress } from '@/modules/dashboard/progress/use-history-query-progress';
import { useTransactionStatusCheck } from '@/modules/dashboard/progress/use-transaction-status-check';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useHistoryStore } from '@/modules/history/use-history-store';

const HUNDRED_EIGHTY_DAYS = 15_552_000_000;

interface UseUnifiedProgressReturn {
  balanceProgress: Ref<BalanceQueryProgress | undefined>;
  dismissalThresholdMs: Readonly<Ref<number, number>>;
  hasTxAccounts: ComputedRef<boolean>;
  historyProgress: Ref<HistoryQueryProgress | undefined>;
  isNeverQueried: ComputedRef<boolean>;
  lastQueriedDisplay: ComputedRef<string>;
  lastQueriedTimestamp: ComputedRef<number>;
  longQuery: ComputedRef<boolean>;
  minOutOfSyncPeriodMs: Readonly<Ref<number, number>>;
  processing: Ref<boolean>;
  processingMessage: ComputedRef<string>;
  processingPercentage: ComputedRef<number>;
  refreshing: ComputedRef<boolean>;
  resetQueryStatus: () => void;
  sectionLoading: ComputedRef<boolean>;
  shouldFetchEventsRegularly: ComputedRef<boolean>;
  showIdleMessage: ComputedRef<boolean>;
  transactionStatusSummary: Ref<TransactionStatus | undefined>;
  queryStatus: Ref<QueryStatusDismissal>;
  navigateToHistory: () => Promise<void>;
  hasUndecodedTransactions: ComputedRef<boolean>;
}

interface QueryStatusDismissal {
  lastBalanceProgressDismissedTs: number;
  lastDismissedTs: number;
  lastUsedVersion: string | null;
}

/**
 * Unified composable for all progress-related functionality.
 * Consolidates balance query progress, history query progress, history events status,
 * and indicator settings into a single composable.
 */
export function useUnifiedProgress(): UseUnifiedProgressReturn {
  const { t } = useI18n({ useScope: 'global' });

  const userId = useLoggedUserIdentifier();

  const queryStatus = useLocalStorage<QueryStatusDismissal>(`${get(userId)}.rotki_query_status`, {
    lastBalanceProgressDismissedTs: 0,
    lastDismissedTs: 0,
    lastUsedVersion: null,
  });

  const { progress: historyProgress } = useHistoryQueryProgress();

  const {
    earliestQueriedTimestamp: lastQueriedTimestamp,
    hasTxAccounts,
    isNeverQueried,
    isOutOfSync: isOutOfSyncCheck,
    navigateToHistory,
    processing,
  } = useTransactionStatusCheck();

  const { balanceProgress, isBalanceQuerying } = useBalanceQueryProgress();
  const { refreshing, sectionLoading, shouldFetchEventsRegularly } = useHistoryEventsStatus();
  const { dismissalThresholdMs, minOutOfSyncPeriodMs } = useHistoryQueryIndicatorSettings();

  const historyStore = useHistoryStore();
  const { transactionStatusSummary } = storeToRefs(historyStore);
  const lastQueriedDisplay = useTimeAgo(lastQueriedTimestamp);

  /**
   * What the indicator says it is doing, or an empty string when it is idle.
   *
   * @remarks
   * A balance or token detection query wins over history events. Both can run at once and the
   * indicator has one line, so the one the user started is the one it reports.
   */
  const processingMessage = computed<string>(() => {
    const balanceProgressData = get(balanceProgress);
    if (balanceProgressData?.currentOperation) {
      return balanceProgressData.currentOperation;
    }

    if (get(processing) && !get(isBalanceQuerying)) {
      const progressData = get(historyProgress);
      if (progressData && progressData.totalSteps > 0) {
        return t('dashboard.history_query_indicator.processing_with_progress', {
          current: progressData.currentStep,
          total: progressData.totalSteps,
        });
      }
      return t('dashboard.history_query_indicator.processing');
    }
    return '';
  });

  /** How far along that work is, following the same precedence as {@link processingMessage}. */
  const processingPercentage = computed<number>(() => {
    const balanceProgressData = get(balanceProgress);
    if (balanceProgressData) {
      return balanceProgressData.percentage;
    }

    if (!get(isBalanceQuerying)) {
      const progressData = get(historyProgress);
      return progressData?.percentage ?? 0;
    }

    return 0;
  });

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
      lastBalanceProgressDismissedTs: 0,
      lastDismissedTs: 0,
      lastUsedVersion: null,
    });
  };

  return {
    balanceProgress,
    dismissalThresholdMs,
    hasTxAccounts,
    hasUndecodedTransactions,
    historyProgress,
    isNeverQueried,
    lastQueriedDisplay,
    lastQueriedTimestamp,
    longQuery,
    minOutOfSyncPeriodMs,
    navigateToHistory,
    processing,
    processingMessage,
    processingPercentage,
    queryStatus,
    refreshing,
    resetQueryStatus,
    sectionLoading,
    shouldFetchEventsRegularly,
    showIdleMessage,
    transactionStatusSummary,
  };
}
