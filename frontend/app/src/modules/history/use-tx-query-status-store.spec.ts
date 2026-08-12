import { createPinia, setActivePinia } from 'pinia';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { TransactionsQueryStatus } from '@/modules/core/messaging/types';
import { type TxQueryStatusData, useTxQueryStatusStore } from './use-tx-query-status-store';

const mockMillisecondsToSeconds = vi.hoisted(() => vi.fn().mockReturnValue(1000));

vi.mock('@/modules/core/common/data/date', () => ({
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
        { address: '0x123', chain: 'eth', subtype: 'evm' as const },
        { address: '0x456', chain: 'optimism', subtype: 'evm' as const },
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

      store.initializeQueryStatus([{ address: '0x123', chain: 'eth', subtype: 'evm' }]);
      expect(Object.keys(get(store.queryStatus))).toHaveLength(1);

      store.initializeQueryStatus([{ address: '0x456', chain: 'optimism', subtype: 'evm' }]);
      expect(Object.keys(get(store.queryStatus))).toHaveLength(1);
      expect(get(store.queryStatus)['0x123eth']).toBeUndefined();
    });

    it('should keep the earlier entries when extending', () => {
      const store = useTxQueryStatusStore();

      store.initializeQueryStatus([{ address: '0x123', chain: 'eth', subtype: 'evm' }]);
      store.initializeQueryStatus([{ address: '0x456', chain: 'optimism', subtype: 'evm' }], { extend: true });

      const status = get(store.queryStatus);
      expect(Object.keys(status)).toHaveLength(2);
      expect(status['0x123eth']).toBeDefined();
      expect(status['0x456optimism']).toBeDefined();
    });

    it('should not walk a finished address back to ACCOUNT_CHANGE when extending', () => {
      const store = useTxQueryStatusStore();
      const account = { address: '0x123', chain: 'eth', subtype: 'evm' as const };

      store.initializeQueryStatus([account]);
      store.setUnifiedTxQueryStatus({
        address: '0x123',
        chain: 'eth',
        period: [0, 1000],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED,
        subtype: 'evm',
      });

      store.initializeQueryStatus([account], { extend: true });

      expect(get(store.queryStatus)['0x123eth'].status).toBe(TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED);
    });

    it('should seed a bitcoin account without a synthetic period', () => {
      const store = useTxQueryStatusStore();

      store.initializeQueryStatus([{ address: 'bc1abc', chain: 'btc', subtype: 'bitcoin' }]);

      const entry = get(store.queryStatus).bc1abcbtc;
      expect(entry).toMatchObject({ address: 'bc1abc', chain: 'btc', subtype: 'bitcoin' });
      // A seeded period would render a progress bar over a range nobody queried.
      expect(entry).not.toHaveProperty('period');
    });

    it('should resume syncing when extending', () => {
      const store = useTxQueryStatusStore();

      store.initializeQueryStatus([{ address: '0x123', chain: 'eth', subtype: 'evm' }]);
      store.stopSyncing();

      store.initializeQueryStatus([{ address: '0x456', chain: 'optimism', subtype: 'evm' }], { extend: true });

      expect(get(store.syncing)).toBe(true);
    });
  });

  describe('setUnifiedTxQueryStatus', () => {
    it('should discard updates when syncing is false', () => {
      const store = useTxQueryStatusStore();

      store.setUnifiedTxQueryStatus({
        address: '0x123',
        chain: 'ETH',
        period: [0, 1000],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED,
        subtype: 'evm',
      });

      expect(Object.keys(get(store.queryStatus))).toHaveLength(0);
    });

    it('should ignore ACCOUNT_CHANGE status', () => {
      const store = useTxQueryStatusStore();
      store.syncing = true;

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
      store.syncing = true;

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

    it('should track a bitcoin period the same way as every other subtype', () => {
      const store = useTxQueryStatusStore();
      store.syncing = true;

      store.setUnifiedTxQueryStatus({
        addresses: ['bc1abc'],
        chain: 'BTC',
        period: [0, 1000],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED,
        subtype: 'bitcoin',
      });

      store.setUnifiedTxQueryStatus({
        addresses: ['bc1abc'],
        chain: 'BTC',
        period: [0, 600],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
        subtype: 'bitcoin',
      });

      expect(get(store.queryStatus).bc1abcbtc).toMatchObject({
        originalPeriodEnd: 1000,
        originalPeriodStart: 600,
        period: [0, 600],
        subtype: 'bitcoin',
      });
    });

    it('should keep a bitcoin period when a later message omits it', () => {
      const store = useTxQueryStatusStore();
      store.syncing = true;

      store.setUnifiedTxQueryStatus({
        addresses: ['bc1abc'],
        chain: 'BTC',
        period: [0, 1000],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED,
        subtype: 'bitcoin',
      });

      // `period` is optional on this subtype alone, so a message without one must not erase what an
      // earlier message established, or the progress bar appears and then vanishes mid-query.
      store.setUnifiedTxQueryStatus({
        addresses: ['bc1abc'],
        chain: 'BTC',
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
        subtype: 'bitcoin',
      });

      expect(get(store.queryStatus).bc1abcbtc).toMatchObject({
        originalPeriodEnd: 1000,
        period: [0, 1000],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
      });
    });

    it('should leave a bitcoin entry period-less when the message carries none', () => {
      const store = useTxQueryStatusStore();
      store.syncing = true;

      store.setUnifiedTxQueryStatus({
        addresses: ['bc1abc'],
        chain: 'BTC',
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED,
        subtype: 'bitcoin',
      });

      const entry = get(store.queryStatus).bc1abcbtc;
      assert(entry.subtype === 'bitcoin');
      expect(entry.period).toBeUndefined();
      expect(entry.originalPeriodEnd).toBeUndefined();
    });

    it('should set originalPeriodEnd from period[1] on STARTED status', () => {
      const store = useTxQueryStatusStore();
      store.syncing = true;

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
      store.syncing = true;

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
      store.syncing = true;

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
      store.syncing = true;

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
      store.syncing = true;

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
      store.syncing = true;

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

    it('should normalize chain to lowercase', () => {
      const store = useTxQueryStatusStore();
      store.syncing = true;

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

    it('should not overwrite cancelled entries with WS updates', () => {
      const store = useTxQueryStatusStore();
      store.syncing = true;

      // Set initial status
      store.setUnifiedTxQueryStatus({
        address: '0x123',
        chain: 'ETH',
        period: [0, 1000],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
        subtype: 'evm',
      });

      // Cancel the address
      store.markAddressCancelled({ address: '0x123', chain: 'eth' });
      expect(get(store.queryStatus)['0x123eth'].status).toBe(TransactionsQueryStatus.CANCELLED);

      // Late WS update should be ignored
      store.setUnifiedTxQueryStatus({
        address: '0x123',
        chain: 'ETH',
        period: [0, 1000],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED,
        subtype: 'evm',
      });

      expect(get(store.queryStatus)['0x123eth'].status).toBe(TransactionsQueryStatus.CANCELLED);
    });

    it('should not overwrite cancelled bitcoin entries with WS updates', () => {
      const store = useTxQueryStatusStore();
      store.syncing = true;

      // Set initial bitcoin status
      store.setUnifiedTxQueryStatus({
        addresses: ['bc1abc'],
        chain: 'BTC',
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED,
        subtype: 'bitcoin',
      });

      // Cancel the address
      store.markAddressCancelled({ address: 'bc1abc', chain: 'btc' });
      expect(get(store.queryStatus).bc1abcbtc.status).toBe(TransactionsQueryStatus.CANCELLED);

      // Late WS update should be ignored
      store.setUnifiedTxQueryStatus({
        addresses: ['bc1abc'],
        chain: 'BTC',
        status: TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED,
        subtype: 'bitcoin',
      });

      expect(get(store.queryStatus).bc1abcbtc.status).toBe(TransactionsQueryStatus.CANCELLED);
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
      expect(status).toHaveProperty('originalPeriodEnd', 1000);
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
      expect(startedStatus).toHaveProperty('originalPeriodEnd', 1000);

      store.setEvmlikeStatus({ address: '0x123', chain: 'scroll' }, 'finished');
      const finishedStatus = get(store.queryStatus)['0x123scroll'];

      expect(hasPeriodsFields(finishedStatus)).toBe(true);
      expect(finishedStatus).toHaveProperty('originalPeriodEnd', 1000);
    });

    it('should not overwrite cancelled entries', () => {
      const store = useTxQueryStatusStore();

      store.setEvmlikeStatus({ address: '0x123', chain: 'scroll' }, 'started');
      store.markAddressCancelled({ address: '0x123', chain: 'scroll' });

      // Trying to set finished should be a no-op since it's cancelled
      store.setEvmlikeStatus({ address: '0x123', chain: 'scroll' }, 'finished');
      expect(get(store.queryStatus)['0x123scroll'].status).toBe(TransactionsQueryStatus.CANCELLED);
    });

    it('should not overwrite failed entries', () => {
      const store = useTxQueryStatusStore();

      store.setEvmlikeStatus({ address: '0x123', chain: 'scroll' }, 'started');
      store.markAddressFailed({ address: '0x123', chain: 'scroll' }, 'evmlike');

      // The caller marks the query failed and then runs its unconditional `finished` tail. Without
      // the guard that tail reports the failed address as complete.
      store.setEvmlikeStatus({ address: '0x123', chain: 'scroll' }, 'finished');
      expect(get(store.queryStatus)['0x123scroll'].status).toBe(TransactionsQueryStatus.FAILED);
    });
  });

  describe('markAddressCancelled', () => {
    it('should set status to CANCELLED', () => {
      const store = useTxQueryStatusStore();
      store.syncing = true;

      store.setUnifiedTxQueryStatus({
        address: '0x123',
        chain: 'ETH',
        period: [0, 1000],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
        subtype: 'evm',
      });

      store.markAddressCancelled({ address: '0x123', chain: 'eth' });

      const status = get(store.queryStatus)['0x123eth'];
      expect(status.status).toBe(TransactionsQueryStatus.CANCELLED);
    });

    it('should preserve other fields when cancelling', () => {
      const store = useTxQueryStatusStore();
      store.syncing = true;

      store.setUnifiedTxQueryStatus({
        address: '0x123',
        chain: 'ETH',
        period: [0, 1000],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
        subtype: 'evm',
      });

      store.markAddressCancelled({ address: '0x123', chain: 'eth' });

      const status = get(store.queryStatus)['0x123eth'];
      expect(status.address).toBe('0x123');
      expect(status.chain).toBe('eth');
      expect(status.subtype).toBe('evm');
    });
  });

  describe('markAddressFailed', () => {
    it('should set status to FAILED, preserving the other fields', () => {
      const store = useTxQueryStatusStore();
      store.syncing = true;

      store.setUnifiedTxQueryStatus({
        address: '0x123',
        chain: 'ETH',
        period: [0, 1000],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
        subtype: 'evm',
      });

      store.markAddressFailed({ address: '0x123', chain: 'eth' });

      const status = get(store.queryStatus)['0x123eth'];
      expect(status.status).toBe(TransactionsQueryStatus.FAILED);
      expect(status.address).toBe('0x123');
      expect(status.chain).toBe('eth');
      expect(status.subtype).toBe('evm');
    });

    it('should create the entry when the query failed before announcing itself', () => {
      const store = useTxQueryStatusStore();
      store.syncing = true;

      store.markAddressFailed({ address: '0x123', chain: 'Gnosis' });

      const status = get(store.queryStatus)['0x123gnosis'];
      expect(status).toBeDefined();
      expect(status.status).toBe(TransactionsQueryStatus.FAILED);
      expect(status.address).toBe('0x123');
      expect(status.chain).toBe('gnosis');
      expect(status.subtype).toBe('evm');
    });

    it('should record the given subtype on a created entry', () => {
      const store = useTxQueryStatusStore();
      store.syncing = true;

      store.markAddressFailed({ address: '0x123', chain: 'zksync_lite' }, 'evmlike');

      const status = get(store.queryStatus)['0x123zksync_lite'];
      expect(status.subtype).toBe('evmlike');
      expect(status.status).toBe(TransactionsQueryStatus.FAILED);
    });

    it('should leave a created entry settled so the run can finish', () => {
      const store = useTxQueryStatusStore();
      store.syncing = true;

      store.setUnifiedTxQueryStatus({
        address: '0xOTHER',
        chain: 'ETH',
        period: [0, 1000],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED,
        subtype: 'evm',
      });

      store.markAddressFailed({ address: '0x123', chain: 'gnosis' });

      // Assert the entry exists as well: with no entry at all `isAllFinished` is vacuously true,
      // so on its own it would pass even if nothing were created.
      expect(get(store.queryStatus)['0x123gnosis']).toBeDefined();
      expect(get(store.isAllFinished)).toBe(true);
    });
  });

  describe('isAddressCancelled', () => {
    it('should return true for cancelled addresses', () => {
      const store = useTxQueryStatusStore();
      store.syncing = true;

      store.setUnifiedTxQueryStatus({
        address: '0x123',
        chain: 'ETH',
        period: [0, 1000],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
        subtype: 'evm',
      });

      store.markAddressCancelled({ address: '0x123', chain: 'eth' });
      expect(store.isAddressCancelled({ address: '0x123', chain: 'eth' })).toBe(true);
    });

    it('should return false for non-cancelled addresses', () => {
      const store = useTxQueryStatusStore();
      store.syncing = true;

      store.setUnifiedTxQueryStatus({
        address: '0x123',
        chain: 'ETH',
        period: [0, 1000],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
        subtype: 'evm',
      });

      expect(store.isAddressCancelled({ address: '0x123', chain: 'eth' })).toBe(false);
    });
  });

  describe('removeQueryStatus', () => {
    it('should remove status for an account', () => {
      const store = useTxQueryStatusStore();

      store.initializeQueryStatus([
        { address: '0x123', chain: 'eth', subtype: 'evm' },
        { address: '0x456', chain: 'optimism', subtype: 'evm' },
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
      store.syncing = true;

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
      store.syncing = true;

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

    it('should settle bitcoin on DECODING_FINISHED', () => {
      const store = useTxQueryStatusStore();
      store.syncing = true;

      store.setUnifiedTxQueryStatus({
        addresses: ['bc1abc'],
        chain: 'BTC',
        status: TransactionsQueryStatus.DECODING_TRANSACTIONS_STARTED,
        subtype: 'bitcoin',
      });

      expect(get(store.isAllFinished)).toBe(false);

      store.setUnifiedTxQueryStatus({
        addresses: ['bc1abc'],
        chain: 'BTC',
        status: TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED,
        subtype: 'bitcoin',
      });

      expect(get(store.isAllFinished)).toBe(true);
    });

    it('should settle bitcoin on QUERYING_FINISHED when no decode follows', () => {
      const store = useTxQueryStatusStore();
      store.syncing = true;

      // The empty-result path: the backend stops at QUERYING_TRANSACTIONS_FINISHED and never sends
      // the decode pair, so requiring the decode left the address querying forever.
      store.setUnifiedTxQueryStatus({
        addresses: ['bc1abc'],
        chain: 'BTC',
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED,
        subtype: 'bitcoin',
      });

      expect(get(store.isAllFinished)).toBe(true);
    });

    it('should treat CANCELLED as finished', () => {
      const store = useTxQueryStatusStore();
      store.syncing = true;

      store.setUnifiedTxQueryStatus({
        address: '0x123',
        chain: 'ETH',
        period: [0, 1000],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
        subtype: 'evm',
      });

      store.markAddressCancelled({ address: '0x123', chain: 'eth' });

      expect(get(store.isAllFinished)).toBe(true);
    });
  });

  describe('resetQueryStatus', () => {
    it('should clear all status entries', () => {
      const store = useTxQueryStatusStore();

      store.initializeQueryStatus([
        { address: '0x123', chain: 'eth', subtype: 'evm' },
        { address: '0x456', chain: 'optimism', subtype: 'evm' },
      ]);

      expect(Object.keys(get(store.queryStatus))).toHaveLength(2);

      store.resetQueryStatus();

      expect(Object.keys(get(store.queryStatus))).toHaveLength(0);
    });
  });
});
