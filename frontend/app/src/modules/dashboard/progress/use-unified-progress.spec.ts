import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useUnifiedProgress } from './use-unified-progress';

interface BalanceProgress {
  currentOperation: string;
  percentage: number;
  currentStep: number;
  totalSteps: number;
  currentOperationData: object;
}

interface HistoryProgress {
  currentStep: number;
  totalSteps: number;
  percentage: number;
}

interface Summary {
  undecodedTxCount: number;
}

const historyProgress = ref<HistoryProgress | undefined>(undefined);
const balanceProgress = ref<BalanceProgress | undefined>(undefined);
const isBalanceQuerying = ref<boolean>(false);
const processing = ref<boolean>(false);
const hasTxAccounts = ref<boolean>(false);
const isNeverQueried = ref<boolean>(false);
const isOutOfSync = ref<boolean>(false);
const earliestQueriedTimestamp = ref<number>(0);
const transactionStatusSummary = ref<Summary | undefined>(undefined);
const dismissalThresholdMs = ref<number>(0);
const minOutOfSyncPeriodMs = ref<number>(0);
const navigateToHistory = vi.fn();

vi.mock('@/modules/auth/use-logged-user-identifier', () => ({
  useLoggedUserIdentifier: (): object => ref('user1'),
}));

vi.mock('@/modules/dashboard/progress/use-history-query-progress', () => ({
  useHistoryQueryProgress: (): object => ({ progress: historyProgress }),
}));

vi.mock('@/modules/dashboard/progress/use-transaction-status-check', () => ({
  useTransactionStatusCheck: (): object => ({
    earliestQueriedTimestamp,
    hasTxAccounts,
    isNeverQueried,
    isOutOfSync,
    navigateToHistory,
    processing,
  }),
}));

vi.mock('@/modules/dashboard/progress/use-balance-query-progress', () => ({
  useBalanceQueryProgress: (): object => ({ balanceProgress, isBalanceQuerying }),
}));

vi.mock('@/modules/history/events/use-history-events-status', () => ({
  useHistoryEventsStatus: (): object => ({
    refreshing: ref(false),
    sectionLoading: ref(false),
    shouldFetchEventsRegularly: ref(false),
  }),
}));

vi.mock('@/modules/dashboard/progress/use-history-query-indicator-settings', () => ({
  useHistoryQueryIndicatorSettings: (): object => ({ dismissalThresholdMs, minOutOfSyncPeriodMs }),
}));

vi.mock('@/modules/history/use-history-store', () => ({
  useHistoryStore: (): object => ({ transactionStatusSummary }),
}));

describe('useUnifiedProgress', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    set(historyProgress, undefined);
    set(balanceProgress, undefined);
    set(isBalanceQuerying, false);
    set(processing, false);
    set(hasTxAccounts, false);
    set(isOutOfSync, false);
    set(earliestQueriedTimestamp, 0);
    set(transactionStatusSummary, undefined);
  });

  describe('processingMessage', () => {
    it('should prioritise the balance operation message', () => {
      set(balanceProgress, { currentOperation: 'Querying', percentage: 10, currentStep: 1, totalSteps: 2, currentOperationData: {} });
      const { processingMessage } = useUnifiedProgress();
      expect(get(processingMessage)).toBe('Querying');
    });

    it('should show history progress when processing and no balance query runs', () => {
      set(processing, true);
      set(historyProgress, { currentStep: 3, totalSteps: 10, percentage: 30 });
      const { processingMessage } = useUnifiedProgress();
      expect(get(processingMessage)).toContain('dashboard.history_query_indicator.processing_with_progress');
    });

    it('should show a generic processing message with no history steps', () => {
      set(processing, true);
      const { processingMessage } = useUnifiedProgress();
      expect(get(processingMessage)).toBe('dashboard.history_query_indicator.processing');
    });

    it('should be empty when idle', () => {
      const { processingMessage } = useUnifiedProgress();
      expect(get(processingMessage)).toBe('');
    });
  });

  describe('processingPercentage', () => {
    it('should use the balance percentage when present', () => {
      set(balanceProgress, { currentOperation: 'x', percentage: 42, currentStep: 1, totalSteps: 2, currentOperationData: {} });
      const { processingPercentage } = useUnifiedProgress();
      expect(get(processingPercentage)).toBe(42);
    });

    it('should fall back to history percentage without a balance query', () => {
      set(historyProgress, { currentStep: 1, totalSteps: 2, percentage: 75 });
      const { processingPercentage } = useUnifiedProgress();
      expect(get(processingPercentage)).toBe(75);
    });

    it('should be 0 while a balance query runs without balance progress', () => {
      set(isBalanceQuerying, true);
      const { processingPercentage } = useUnifiedProgress();
      expect(get(processingPercentage)).toBe(0);
    });
  });

  describe('showIdleMessage', () => {
    it('should be false without accounts', () => {
      set(isOutOfSync, true);
      const { showIdleMessage } = useUnifiedProgress();
      expect(get(showIdleMessage)).toBe(false);
    });

    it('should mirror the out-of-sync check when accounts exist', () => {
      set(hasTxAccounts, true);
      set(isOutOfSync, true);
      const { showIdleMessage } = useUnifiedProgress();
      expect(get(showIdleMessage)).toBe(true);
    });
  });

  describe('longQuery', () => {
    it('should be true when queried long ago with no undecoded transactions', () => {
      set(hasTxAccounts, true);
      set(earliestQueriedTimestamp, 0);
      set(transactionStatusSummary, { undecodedTxCount: 0 });
      const { longQuery } = useUnifiedProgress();
      expect(get(longQuery)).toBe(true);
    });

    it('should be false when there are undecoded transactions', () => {
      set(hasTxAccounts, true);
      set(earliestQueriedTimestamp, 0);
      set(transactionStatusSummary, { undecodedTxCount: 5 });
      const { longQuery } = useUnifiedProgress();
      expect(get(longQuery)).toBe(false);
    });
  });

  describe('hasUndecodedTransactions', () => {
    it('should be true when the count is positive', () => {
      set(transactionStatusSummary, { undecodedTxCount: 2 });
      const { hasUndecodedTransactions } = useUnifiedProgress();
      expect(get(hasUndecodedTransactions)).toBe(true);
    });

    it('should be false when the count is zero', () => {
      set(transactionStatusSummary, { undecodedTxCount: 0 });
      const { hasUndecodedTransactions } = useUnifiedProgress();
      expect(get(hasUndecodedTransactions)).toBe(false);
    });

    it('should be false without a summary', () => {
      const { hasUndecodedTransactions } = useUnifiedProgress();
      expect(get(hasUndecodedTransactions)).toBe(false);
    });
  });

  describe('resetQueryStatus', () => {
    it('should restore the dismissal defaults', () => {
      const { queryStatus, resetQueryStatus } = useUnifiedProgress();
      set(queryStatus, { lastBalanceProgressDismissedTs: 5, lastDismissedTs: 5, lastUsedVersion: '1.0' });
      resetQueryStatus();
      expect(get(queryStatus)).toEqual({
        lastBalanceProgressDismissedTs: 0,
        lastDismissedTs: 0,
        lastUsedVersion: null,
      });
    });
  });
});
