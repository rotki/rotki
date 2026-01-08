import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { TransactionsQueryStatus } from '@/modules/messaging/types';
import { type TxQueryStatusData, useTxQueryStatusStore } from './tx-query-status';

const mockMillisecondsToSeconds = vi.hoisted(() => vi.fn().mockReturnValue(1000));

vi.mock('@/utils/date', () => ({
  millisecondsToSeconds: mockMillisecondsToSeconds,
}));

// Type guard to check if status has period-related fields (EVM/EvmLike/Solana)
function hasPeriodsFields(status: TxQueryStatusData): status is TxQueryStatusData & {
  period: [number, number];
  originalPeriodEnd?: number;
  originalPeriodStart?: number;
} {
  return status.subtype !== 'bitcoin';
}

describe('store/history/query-status/tx-query-status', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    // Reset mock return value after clearAllMocks
    mockMillisecondsToSeconds.mockReturnValue(1000);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('initializeQueryStatus', () => {
    it('should initialize status for multiple accounts', () => {
      const store = useTxQueryStatusStore();
      const accounts = [
        { address: '0x123', chain: 'eth' },
        { address: '0x456', chain: 'optimism' },
      ];

      store.initializeQueryStatus(accounts);

      const status = get(store.queryStatus);
      expect(Object.keys(status)).toHaveLength(2);
      expect(status['0x123eth']).toMatchObject({
        address: '0x123',
        chain: 'eth',
        status: TransactionsQueryStatus.ACCOUNT_CHANGE,
        subtype: 'evm',
      });
    });

    it('should reset existing status before initializing', () => {
      const store = useTxQueryStatusStore();

      store.initializeQueryStatus([{ address: '0x123', chain: 'eth' }]);
      expect(Object.keys(get(store.queryStatus))).toHaveLength(1);

      store.initializeQueryStatus([{ address: '0x456', chain: 'optimism' }]);
      expect(Object.keys(get(store.queryStatus))).toHaveLength(1);
      expect(get(store.queryStatus)['0x123eth']).toBeUndefined();
    });
  });

  describe('setUnifiedTxQueryStatus', () => {
    it('should ignore ACCOUNT_CHANGE status', () => {
      const store = useTxQueryStatusStore();

      store.setUnifiedTxQueryStatus({
        address: '0x123',
        chain: 'ETH',
        period: [0, 1000],
        status: TransactionsQueryStatus.ACCOUNT_CHANGE,
        subtype: 'evm',
      });

      expect(Object.keys(get(store.queryStatus))).toHaveLength(0);
    });

    it('should handle bitcoin transactions with multiple addresses', () => {
      const store = useTxQueryStatusStore();

      store.setUnifiedTxQueryStatus({
        addresses: ['bc1abc', 'bc1def'],
        chain: 'BTC',
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED,
        subtype: 'bitcoin',
      });

      const status = get(store.queryStatus);
      expect(Object.keys(status)).toHaveLength(2);
      expect(status.bc1abcbtc).toMatchObject({
        address: 'bc1abc',
        chain: 'btc',
        subtype: 'bitcoin',
      });
      expect(status.bc1defbtc).toMatchObject({
        address: 'bc1def',
        chain: 'btc',
        subtype: 'bitcoin',
      });
    });

    describe('evm transaction status', () => {
      it('should set originalPeriodEnd from period[1] on STARTED status', () => {
        const store = useTxQueryStatusStore();

        store.setUnifiedTxQueryStatus({
          address: '0x123',
          chain: 'ETH',
          period: [0, 2000],
          status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED,
          subtype: 'evm',
        });

        const status = get(store.queryStatus)['0x123eth'];
        expect(hasPeriodsFields(status) && status.originalPeriodEnd).toBe(2000);
      });

      it('should preserve originalPeriodEnd on subsequent updates', () => {
        const store = useTxQueryStatusStore();

        // First: STARTED with period end
        store.setUnifiedTxQueryStatus({
          address: '0x123',
          chain: 'ETH',
          period: [0, 2000],
          status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED,
          subtype: 'evm',
        });

        // Update: Status changes but originalPeriodEnd preserved
        store.setUnifiedTxQueryStatus({
          address: '0x123',
          chain: 'ETH',
          period: [0, 1500],
          status: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
          subtype: 'evm',
        });

        const status = get(store.queryStatus)['0x123eth'];
        expect(hasPeriodsFields(status) && status.originalPeriodEnd).toBe(2000);
        expect(hasPeriodsFields(status) && status.period).toEqual([0, 1500]);
      });

      it('should NOT set originalPeriodStart from STARTED status period[1]', () => {
        const store = useTxQueryStatusStore();

        // STARTED status should only set originalPeriodEnd, not originalPeriodStart
        // This is the fix for the 100% progress bug
        store.setUnifiedTxQueryStatus({
          address: '0x123',
          chain: 'ETH',
          period: [0, 2000],
          status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED,
          subtype: 'evm',
        });

        const status = get(store.queryStatus)['0x123eth'];
        // originalPeriodStart should NOT be set from STARTED status
        expect(hasPeriodsFields(status) && status.originalPeriodStart).toBeUndefined();
      });

      it('should set originalPeriodStart from first QUERYING status with non-zero period[1]', () => {
        const store = useTxQueryStatusStore();

        // STARTED status - should NOT set originalPeriodStart
        store.setUnifiedTxQueryStatus({
          address: '0x123',
          chain: 'ETH',
          period: [0, 2000],
          status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED,
          subtype: 'evm',
        });

        // First QUERYING status - should set originalPeriodStart
        store.setUnifiedTxQueryStatus({
          address: '0x123',
          chain: 'ETH',
          period: [0, 1800],
          status: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
          subtype: 'evm',
        });

        const status = get(store.queryStatus)['0x123eth'];
        expect(hasPeriodsFields(status) && status.originalPeriodStart).toBe(1800);
        expect(hasPeriodsFields(status) && status.originalPeriodEnd).toBe(2000);
      });

      it('should use period[0] as originalPeriodStart when non-zero', () => {
        const store = useTxQueryStatusStore();

        store.setUnifiedTxQueryStatus({
          address: '0x123',
          chain: 'ETH',
          period: [500, 2000],
          status: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
          subtype: 'evm',
        });

        const status = get(store.queryStatus)['0x123eth'];
        expect(hasPeriodsFields(status) && status.originalPeriodStart).toBe(500);
      });

      it('should preserve originalPeriodStart on subsequent updates', () => {
        const store = useTxQueryStatusStore();

        // First update sets originalPeriodStart
        store.setUnifiedTxQueryStatus({
          address: '0x123',
          chain: 'ETH',
          period: [0, 1800],
          status: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
          subtype: 'evm',
        });

        // Subsequent update should preserve originalPeriodStart
        store.setUnifiedTxQueryStatus({
          address: '0x123',
          chain: 'ETH',
          period: [0, 1500],
          status: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
          subtype: 'evm',
        });

        const status = get(store.queryStatus)['0x123eth'];
        expect(hasPeriodsFields(status) && status.originalPeriodStart).toBe(1800);
        expect(hasPeriodsFields(status) && status.period).toEqual([0, 1500]);
      });
    });

    it('should normalize chain to lowercase', () => {
      const store = useTxQueryStatusStore();

      store.setUnifiedTxQueryStatus({
        address: '0x123',
        chain: 'OPTIMISM',
        period: [0, 1000],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED,
        subtype: 'evm',
      });

      const status = get(store.queryStatus);
      expect(status['0x123optimism']).toBeDefined();
      expect(status['0x123optimism'].chain).toBe('optimism');
    });
  });

  describe('setEvmlikeStatus', () => {
    it('should set started status for evmlike chains', () => {
      const store = useTxQueryStatusStore();

      store.setEvmlikeStatus({ address: '0x123', chain: 'scroll' }, 'started');

      const status = get(store.queryStatus)['0x123scroll'];
      expect(status).toMatchObject({
        address: '0x123',
        chain: 'scroll',
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED,
        subtype: 'evmlike',
      });
      expect(hasPeriodsFields(status)).toBe(true);
      if (hasPeriodsFields(status)) {
        expect(status.originalPeriodEnd).toBe(1000);
      }
    });

    it('should set finished status for evmlike chains', () => {
      const store = useTxQueryStatusStore();

      store.setEvmlikeStatus({ address: '0x123', chain: 'scroll' }, 'started');
      store.setEvmlikeStatus({ address: '0x123', chain: 'scroll' }, 'finished');

      const status = get(store.queryStatus)['0x123scroll'];
      expect(status.status).toBe(TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED);
    });

    it('should preserve originalPeriodEnd when finishing', () => {
      const store = useTxQueryStatusStore();

      store.setEvmlikeStatus({ address: '0x123', chain: 'scroll' }, 'started');
      const startedStatus = get(store.queryStatus)['0x123scroll'];
      expect(hasPeriodsFields(startedStatus)).toBe(true);
      const originalEnd = hasPeriodsFields(startedStatus) ? startedStatus.originalPeriodEnd : undefined;

      store.setEvmlikeStatus({ address: '0x123', chain: 'scroll' }, 'finished');
      const finishedStatus = get(store.queryStatus)['0x123scroll'];

      expect(hasPeriodsFields(finishedStatus)).toBe(true);
      if (hasPeriodsFields(finishedStatus)) {
        expect(finishedStatus.originalPeriodEnd).toBe(originalEnd);
      }
    });
  });

  describe('removeQueryStatus', () => {
    it('should remove status for an account', () => {
      const store = useTxQueryStatusStore();

      store.initializeQueryStatus([
        { address: '0x123', chain: 'eth' },
        { address: '0x456', chain: 'optimism' },
      ]);

      store.removeQueryStatus({ address: '0x123', chain: 'eth' });

      const status = get(store.queryStatus);
      expect(status['0x123eth']).toBeUndefined();
      expect(status['0x456optimism']).toBeDefined();
    });
  });

  describe('isAllFinished', () => {
    it('should return true when all EVM statuses are finished', () => {
      const store = useTxQueryStatusStore();

      store.setUnifiedTxQueryStatus({
        address: '0x123',
        chain: 'ETH',
        period: [0, 1000],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED,
        subtype: 'evm',
      });

      store.setUnifiedTxQueryStatus({
        address: '0x456',
        chain: 'OPTIMISM',
        period: [0, 1000],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED,
        subtype: 'evm',
      });

      expect(get(store.isAllFinished)).toBe(true);
    });

    it('should return false when any EVM status is not finished', () => {
      const store = useTxQueryStatusStore();

      store.setUnifiedTxQueryStatus({
        address: '0x123',
        chain: 'ETH',
        period: [0, 1000],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED,
        subtype: 'evm',
      });

      store.setUnifiedTxQueryStatus({
        address: '0x456',
        chain: 'OPTIMISM',
        period: [0, 1000],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
        subtype: 'evm',
      });

      expect(get(store.isAllFinished)).toBe(false);
    });

    it('should use DECODING_FINISHED for bitcoin status', () => {
      const store = useTxQueryStatusStore();

      store.setUnifiedTxQueryStatus({
        addresses: ['bc1abc'],
        chain: 'BTC',
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED,
        subtype: 'bitcoin',
      });

      // Bitcoin uses DECODING_TRANSACTIONS_FINISHED as the finished status
      expect(get(store.isAllFinished)).toBe(false);

      store.setUnifiedTxQueryStatus({
        addresses: ['bc1abc'],
        chain: 'BTC',
        status: TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED,
        subtype: 'bitcoin',
      });

      expect(get(store.isAllFinished)).toBe(true);
    });
  });

  describe('resetQueryStatus', () => {
    it('should clear all status entries', () => {
      const store = useTxQueryStatusStore();

      store.initializeQueryStatus([
        { address: '0x123', chain: 'eth' },
        { address: '0x456', chain: 'optimism' },
      ]);

      expect(Object.keys(get(store.queryStatus))).toHaveLength(2);

      store.resetQueryStatus();

      expect(Object.keys(get(store.queryStatus))).toHaveLength(0);
    });
  });
});
