import type { ComputedRef, Ref } from 'vue';
import type { EvmTransactionStatus } from '@/composables/api/history/events';
import type { BlockchainAccount } from '@/types/blockchain/accounts';
import { get, isDefined } from '@vueuse/shared';
import { useSupportedChains } from '@/composables/info/chains';
import { useRefWithDebounce } from '@/composables/ref';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { type BalanceQueryProgress, useBalanceQueryProgress } from '@/modules/dashboard/progress/composables/use-balance-query-progress';
import { useHistoryQueryIndicatorSettings } from '@/modules/dashboard/progress/composables/use-history-query-indicator-settings';
import { type HistoryQueryProgress, useHistoryQueryProgress } from '@/modules/dashboard/progress/composables/use-history-query-progress';
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
  sectionLoading: ComputedRef<boolean>;
  shouldFetchEventsRegularly: ComputedRef<boolean>;
  showIdleMessage: ComputedRef<boolean>;
  transactionStatus: Ref<EvmTransactionStatus | undefined>;
}

/**
 * Unified composable for all progress-related functionality.
 * Consolidates balance query progress, history query progress, history events status,
 * and indicator settings into a single composable.
 */
export function useUnifiedProgress(): UseUnifiedProgressReturn {
  const { t } = useI18n({ useScope: 'global' });

  // Use existing composables
  const { progress: historyProgress } = useHistoryQueryProgress();
  const { balanceProgress, isBalanceQuerying } = useBalanceQueryProgress();
  const { processing: rawProcessing, refreshing, sectionLoading, shouldFetchEventsRegularly } = useHistoryEventsStatus();
  const { dismissalThresholdMs, minOutOfSyncPeriodMs } = useHistoryQueryIndicatorSettings();

  // Additional stores and composables
  const historyStore = useHistoryStore();
  const { evmTransactionStatus: transactionStatus } = storeToRefs(historyStore);
  const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());
  const { allTxChainsInfo } = useSupportedChains();

  const processing = useRefWithDebounce(rawProcessing, 400);

  const txChainIds = useArrayMap(allTxChainsInfo, x => x.id);

  const accounts = computed<BlockchainAccount[]>(() =>
    Object.values(get(accountsPerChain))
      .flatMap(x => x)
      .filter(hasAccountAddress),
  );

  const hasTxAccounts = computed<boolean>(() => {
    const { hasEvmAccounts = false } = get(transactionStatus) ?? {};
    if (!hasEvmAccounts) {
      return false;
    }
    const filteredChains = get(txChainIds);
    return get(accounts).some(({ chain }) => filteredChains.includes(chain));
  });

  const lastQueriedTimestamp = computed<number>(() => {
    const status = get(transactionStatus);
    if (!status || status.lastQueriedTs === 0)
      return 0;

    // Convert seconds to milliseconds for useTimeAgo
    return status.lastQueriedTs * 1000;
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
    const status = get(transactionStatus);
    if (!isDefined(status)) {
      return false;
    }

    const now = Date.now();
    const lastQueriedTs = get(lastQueriedTimestamp);
    const minOutOfSyncMs = get(minOutOfSyncPeriodMs);

    // Don't show if not out of sync enough
    return now - lastQueriedTs >= minOutOfSyncMs;
  });

  const isNeverQueried = computed<boolean>(() => {
    const status = get(transactionStatus);
    return isDefined(status) && status.lastQueriedTs === 0;
  });

  const longQuery = computed<boolean>(() => {
    const status = get(transactionStatus);
    const now = Date.now();
    return isDefined(status) && status.undecodedTxCount === 0 && now - status.lastQueriedTs > HUNDRED_EIGHTY_DAYS;
  });

  return {
    balanceProgress,
    dismissalThresholdMs,
    hasTxAccounts,
    historyProgress,
    isNeverQueried,
    lastQueriedDisplay,
    lastQueriedTimestamp,
    longQuery,
    minOutOfSyncPeriodMs,
    processing,
    processingMessage,
    processingPercentage,
    refreshing,
    sectionLoading,
    shouldFetchEventsRegularly,
    showIdleMessage,
    transactionStatus,
  };
}
