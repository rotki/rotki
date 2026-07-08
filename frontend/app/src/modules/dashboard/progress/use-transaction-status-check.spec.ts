import type { Ref } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Routes } from '@/router/routes';
import { useTransactionStatusCheck } from './use-transaction-status-check';

interface Summary {
  hasEvmAccounts?: boolean;
  hasExchangesAccounts?: boolean;
  evmLastQueriedTs?: number;
  exchangesLastQueriedTs?: number;
}

const transactionStatusSummary = ref<Summary | undefined>(undefined);
const minOutOfSyncPeriodMs = ref<number>(60 * 60 * 1000);
const rawProcessing = ref<boolean>(false);
const push = vi.fn();

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>();
  return { ...actual, useRouter: (): object => ({ push }) };
});

vi.mock('@/modules/history/use-history-store', () => ({
  useHistoryStore: (): object => ({ transactionStatusSummary }),
}));

vi.mock('@/modules/dashboard/progress/use-history-query-indicator-settings', () => ({
  useHistoryQueryIndicatorSettings: (): object => ({ minOutOfSyncPeriodMs }),
}));

vi.mock('@/modules/history/events/use-history-events-status', () => ({
  useHistoryEventsStatus: (): object => ({ processing: rawProcessing }),
}));

vi.mock('@/modules/core/common/use-ref-debounce', () => ({
  useRefWithDebounce: (value: Ref<boolean>): Ref<boolean> => value,
}));

function nowSeconds(): number {
  return Math.floor(Date.now() / 1000);
}

describe('useTransactionStatusCheck', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(transactionStatusSummary, undefined);
    set(minOutOfSyncPeriodMs, 60 * 60 * 1000);
    set(rawProcessing, false);
  });

  describe('hasTxAccounts', () => {
    it('should be false without a summary', () => {
      const { hasTxAccounts } = useTransactionStatusCheck();
      expect(get(hasTxAccounts)).toBe(false);
    });

    it('should be true when evm accounts exist', () => {
      set(transactionStatusSummary, { hasEvmAccounts: true });
      const { hasTxAccounts } = useTransactionStatusCheck();
      expect(get(hasTxAccounts)).toBe(true);
    });
  });

  describe('earliestQueriedTimestamp', () => {
    it('should be 0 when there are no accounts', () => {
      const { earliestQueriedTimestamp } = useTransactionStatusCheck();
      expect(get(earliestQueriedTimestamp)).toBe(0);
    });

    it('should return the earliest timestamp in milliseconds', () => {
      set(transactionStatusSummary, {
        hasEvmAccounts: true,
        hasExchangesAccounts: true,
        evmLastQueriedTs: 2000,
        exchangesLastQueriedTs: 1000,
      });
      const { earliestQueriedTimestamp } = useTransactionStatusCheck();
      expect(get(earliestQueriedTimestamp)).toBe(1000 * 1000);
    });

    it('should be 0 when accounts exist but were never queried', () => {
      set(transactionStatusSummary, { hasEvmAccounts: true, evmLastQueriedTs: 0 });
      const { earliestQueriedTimestamp } = useTransactionStatusCheck();
      expect(get(earliestQueriedTimestamp)).toBe(0);
    });
  });

  describe('isNeverQueried', () => {
    it('should be true when accounts exist but earliest timestamp is 0', () => {
      set(transactionStatusSummary, { hasEvmAccounts: true, evmLastQueriedTs: 0 });
      const { isNeverQueried } = useTransactionStatusCheck();
      expect(get(isNeverQueried)).toBe(true);
    });

    it('should be false once queried', () => {
      set(transactionStatusSummary, { hasEvmAccounts: true, evmLastQueriedTs: nowSeconds() });
      const { isNeverQueried } = useTransactionStatusCheck();
      expect(get(isNeverQueried)).toBe(false);
    });
  });

  describe('isOutOfSync', () => {
    it('should be false without accounts', () => {
      const { isOutOfSync } = useTransactionStatusCheck();
      expect(get(isOutOfSync)).toBe(false);
    });

    it('should be true when the last query is older than the threshold', () => {
      set(transactionStatusSummary, { hasEvmAccounts: true, evmLastQueriedTs: 1000 });
      const { isOutOfSync } = useTransactionStatusCheck();
      expect(get(isOutOfSync)).toBe(true);
    });

    it('should be false when recently queried', () => {
      set(transactionStatusSummary, { hasEvmAccounts: true, evmLastQueriedTs: nowSeconds() });
      const { isOutOfSync } = useTransactionStatusCheck();
      expect(get(isOutOfSync)).toBe(false);
    });
  });

  describe('navigateToHistory', () => {
    it('should push the history events route', async () => {
      const { navigateToHistory } = useTransactionStatusCheck();
      await navigateToHistory();
      expect(push).toHaveBeenCalledWith(Routes.HISTORY_EVENTS);
    });
  });

  it('should expose the debounced processing ref', () => {
    set(rawProcessing, true);
    const { processing } = useTransactionStatusCheck();
    expect(get(processing)).toBe(true);
  });
});
