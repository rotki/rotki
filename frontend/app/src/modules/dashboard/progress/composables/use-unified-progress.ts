import type { ComputedRef, Ref } from 'vue';
import type { TransactionStatus } from '@/composables/api/history/events';
import type { BlockchainAccount } from '@/types/blockchain/accounts';
import { get, isDefined, set } from '@vueuse/shared';
import { useSupportedChains } from '@/composables/info/chains';
import { useLoggedUserIdentifier } from '@/composables/user/use-logged-user-identifier';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { type BalanceQueryProgress, useBalanceQueryProgress } from '@/modules/dashboard/progress/composables/use-balance-query-progress';
import { useHistoryQueryIndicatorSettings } from '@/modules/dashboard/progress/composables/use-history-query-indicator-settings';
import { type HistoryQueryProgress, useHistoryQueryProgress } from '@/modules/dashboard/progress/composables/use-history-query-progress';
import { useTransactionStatusCheck } from '@/modules/dashboard/progress/composables/use-transaction-status-check';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useHistoryStore } from '@/store/history';
import { hasAccountAddress } from '@/utils/blockchain/accounts';

const HUNDRED_EIGHTY_DAYS = 15_552_000_000;

interface UseUnifiedProgressReturn {
  // Balance query progress
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

  // Use existing composables
  const { progress: historyProgress } = useHistoryQueryProgress();

  const {
    earliestQueriedTimestamp: lastQueriedTimestamp,
    isAccountsExist,
    isNeverQueried,
    isOutOfSync: isOutOfSyncCheck,
    navigateToHistory,
    processing,
  } = useTransactionStatusCheck();

  const { balanceProgress, isBalanceQuerying } = useBalanceQueryProgress();
  const { refreshing, sectionLoading, shouldFetchEventsRegularly } = useHistoryEventsStatus();
  const { dismissalThresholdMs, minOutOfSyncPeriodMs } = useHistoryQueryIndicatorSettings();

  // Additional stores and composables
  const historyStore = useHistoryStore();
  const { transactionStatusSummary } = storeToRefs(historyStore);
  const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());
  const { allTxChainsInfo } = useSupportedChains();

  const txChainIds = useArrayMap(allTxChainsInfo, x => x.id);

  const accounts = computed<BlockchainAccount[]>(() =>
    Object.values(get(accountsPerChain))
      .flatMap(x => x)
      .filter(hasAccountAddress),
  );

  const hasTxAccounts = computed<boolean>(() => {
    const { hasEvmAccounts = false } = get(transactionStatusSummary) ?? {};
    if (!hasEvmAccounts) {
      return false;
    }
    const filteredChains = get(txChainIds);
    return get(accounts).some(({ chain }) => filteredChains.includes(chain));
  });

  const lastQueriedDisplay = useTimeAgo(lastQueriedTimestamp);

  const processingMessage = computed<string>(() => {
    // Prioritize balance/token detection over history events
    const balanceProgressData = get(balanceProgress);
    if (balanceProgressData && balanceProgressData.currentOperation) {
      return balanceProgressData.currentOperation;
    }

    // Only show history events progress if no balance queries are running
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

  const processingPercentage = computed<number>(() => {
    // Prioritize balance/token detection percentage
    const balanceProgressData = get(balanceProgress);
    if (balanceProgressData) {
      return balanceProgressData.percentage;
    }

    // Use history progress if no balance queries
    if (!get(isBalanceQuerying)) {
      const progressData = get(historyProgress);
      return progressData?.percentage ?? 0;
    }

    return 0;
  });

  const showIdleMessage = computed<boolean>(() => {
    if (!get(isAccountsExist)) {
      return false;
    }

    return get(isOutOfSyncCheck);
  });

  const longQuery = computed<boolean>(() => {
    if (!get(isAccountsExist)) {
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
