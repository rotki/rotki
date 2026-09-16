import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useUnifiedProgress } from './use-unified-progress';

interface Summary {
  undecodedTxCount: number;
}

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
    set(processing, false);
    set(hasTxAccounts, false);
    set(isOutOfSync, false);
    set(earliestQueriedTimestamp, 0);
    set(transactionStatusSummary, undefined);
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
      set(queryStatus, { lastDismissedTs: 5, lastUsedVersion: '1.0' });
      resetQueryStatus();
      expect(get(queryStatus)).toEqual({
        lastDismissedTs: 0,
        lastUsedVersion: null,
      });
    });
  });
});
