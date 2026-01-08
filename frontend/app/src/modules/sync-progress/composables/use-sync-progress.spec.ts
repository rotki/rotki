import { beforeEach, describe, expect, it } from 'vitest';
import {
  type EvmUnDecodedTransactionsData,
  type HistoryEventsQueryData,
  HistoryEventsQueryStatus,
  type ProtocolCacheUpdatesData,
  TransactionsQueryStatus,
  type UnifiedTransactionStatusData,
} from '@/modules/messaging/types';
import { useHistoryStore } from '@/store/history';
import { useEventsQueryStatusStore } from '@/store/history/query-status/events-query-status';
import { useTxQueryStatusStore } from '@/store/history/query-status/tx-query-status';
import { LocationStatus, SyncPhase } from '../types';
import { useSyncProgress } from './use-sync-progress';

describe('useSyncProgress', () => {
  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
  });

  const createEvmTxStatus = (
    address: string,
    chain: string,
    status: TransactionsQueryStatus,
  ): UnifiedTransactionStatusData => ({
    address,
    chain,
    period: [0, 500] as [number, number],
    status,
    subtype: 'evm',
  });

  const createEventsStatus = (
    location: string,
    name: string,
    status: HistoryEventsQueryStatus,
  ): HistoryEventsQueryData => ({
    eventType: 'trade',
    location,
    name,
    period: [0, 1000],
    status,
  });

  const createDecodingStatus = (
    chain: string,
    total: number,
    processed: number,
  ): EvmUnDecodedTransactionsData => ({
    chain,
    processed,
    total,
  });

  const createProtocolCacheStatus = (
    chain: string,
    protocol: string,
    total: number,
    processed: number,
  ): ProtocolCacheUpdatesData => ({
    chain,
    processed,
    protocol,
    total,
  });

  const setupTxStore = (statuses: UnifiedTransactionStatusData[]): void => {
    const txStore = useTxQueryStatusStore();
    // First initialize with addresses
    const addresses = statuses
      .filter((s): s is UnifiedTransactionStatusData & { address: string } => 'address' in s)
      .map(s => ({ address: s.address, chain: s.chain }));
    txStore.initializeQueryStatus(addresses);
    // Then update each status
    for (const status of statuses) {
      txStore.setUnifiedTxQueryStatus(status);
    }
  };

  const setupEventsStore = (statuses: HistoryEventsQueryData[]): void => {
    const eventsStore = useEventsQueryStatusStore();
    eventsStore.initializeQueryStatus(statuses.map(s => ({ location: s.location, name: s.name })));
    for (const status of statuses) {
      eventsStore.setQueryStatus(status);
    }
  };

  describe('phase detection', () => {
    it('should return IDLE when no activity', () => {
      const { phase } = useSyncProgress();
      expect(get(phase)).toBe(SyncPhase.IDLE);
    });

    it('should return SYNCING when there is activity', () => {
      setupTxStore([
        createEvmTxStatus('0x123', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      ]);

      const { phase } = useSyncProgress();
      expect(get(phase)).toBe(SyncPhase.SYNCING);
    });

    it('should return COMPLETE when all activities are finished', () => {
      setupTxStore([
        createEvmTxStatus('0x123', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
      ]);

      setupEventsStore([
        createEventsStatus('kraken', 'Kraken', HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED),
      ]);

      const { phase } = useSyncProgress();
      expect(get(phase)).toBe(SyncPhase.COMPLETE);
    });
  });

  describe('isActive', () => {
    it('should be false when no activity', () => {
      const { isActive } = useSyncProgress();
      expect(get(isActive)).toBe(false);
    });

    it('should be true when there are transaction queries', () => {
      setupTxStore([
        createEvmTxStatus('0x123', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      ]);

      const { isActive } = useSyncProgress();
      expect(get(isActive)).toBe(true);
    });

    it('should be true when there are events queries', () => {
      setupEventsStore([
        createEventsStatus('kraken', 'Kraken', HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE),
      ]);

      const { isActive } = useSyncProgress();
      expect(get(isActive)).toBe(true);
    });

    it('should be true when there is decoding activity', () => {
      const historyStore = useHistoryStore();
      historyStore.setUndecodedTransactionsStatus(createDecodingStatus('eth', 100, 50));

      const { isActive } = useSyncProgress();
      expect(get(isActive)).toBe(true);
    });
  });

  describe('location progress', () => {
    it('should map location statuses correctly', () => {
      setupEventsStore([
        createEventsStatus('kraken', 'Kraken', HistoryEventsQueryStatus.QUERYING_EVENTS_STARTED),
        createEventsStatus('binance', 'Binance', HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE),
        createEventsStatus('coinbase', 'Coinbase', HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED),
      ]);

      const { locations } = useSyncProgress();
      const locationsValue = get(locations);

      const krakenLocation = locationsValue.find(l => l.location === 'kraken');
      const binanceLocation = locationsValue.find(l => l.location === 'binance');
      const coinbaseLocation = locationsValue.find(l => l.location === 'coinbase');

      expect(krakenLocation?.status).toBe(LocationStatus.PENDING);
      expect(binanceLocation?.status).toBe(LocationStatus.QUERYING);
      expect(coinbaseLocation?.status).toBe(LocationStatus.COMPLETE);
    });

    it('should sort locations with querying first', () => {
      setupEventsStore([
        createEventsStatus('kraken', 'Kraken', HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED),
        createEventsStatus('binance', 'Binance', HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE),
        createEventsStatus('coinbase', 'Coinbase', HistoryEventsQueryStatus.QUERYING_EVENTS_STARTED),
      ]);

      const { locations } = useSyncProgress();
      const locationsValue = get(locations);

      expect(locationsValue[0].status).toBe(LocationStatus.QUERYING);
      expect(locationsValue[1].status).toBe(LocationStatus.PENDING);
      expect(locationsValue[2].status).toBe(LocationStatus.COMPLETE);
    });
  });

  describe('decoding progress', () => {
    it('should calculate decoding progress correctly', () => {
      const historyStore = useHistoryStore();
      historyStore.setUndecodedTransactionsStatus(createDecodingStatus('eth', 100, 50));

      const { decoding } = useSyncProgress();
      const decodingValue = get(decoding);

      expect(decodingValue).toHaveLength(1);
      expect(decodingValue[0].chain).toBe('eth');
      expect(decodingValue[0].total).toBe(100);
      expect(decodingValue[0].processed).toBe(50);
      expect(decodingValue[0].progress).toBe(50);
    });

    it('should filter out chains with total 0', () => {
      const historyStore = useHistoryStore();
      historyStore.setUndecodedTransactionsStatus(createDecodingStatus('eth', 0, 0));

      const { decoding } = useSyncProgress();
      const decodingValue = get(decoding);

      // Chains with total = 0 are filtered out by decodingSyncStatus
      expect(decodingValue).toHaveLength(0);
    });
  });

  describe('protocol cache progress', () => {
    it('should calculate protocol cache progress correctly', () => {
      const historyStore = useHistoryStore();
      historyStore.setProtocolCacheStatus(createProtocolCacheStatus('eth', 'uniswap', 200, 100));

      const { protocolCache } = useSyncProgress();
      const protocolCacheValue = get(protocolCache);

      expect(protocolCacheValue).toHaveLength(1);
      expect(protocolCacheValue[0].chain).toBe('eth');
      expect(protocolCacheValue[0].protocol).toBe('uniswap');
      expect(protocolCacheValue[0].total).toBe(200);
      expect(protocolCacheValue[0].processed).toBe(100);
      expect(protocolCacheValue[0].progress).toBe(50);
    });
  });

  describe('overall progress', () => {
    it('should return 0 when no activity', () => {
      const { overallProgress } = useSyncProgress();
      expect(get(overallProgress)).toBe(0);
    });

    it('should calculate weighted progress with transactions only', () => {
      setupTxStore([
        createEvmTxStatus('0x123', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
        createEvmTxStatus('0x456', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      ]);

      const { overallProgress } = useSyncProgress();
      // 1 of 2 accounts completed = 50%
      // Only transactions weight applies
      expect(get(overallProgress)).toBe(50);
    });

    it('should calculate weighted progress with multiple activity types', () => {
      setupTxStore([
        createEvmTxStatus('0x123', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
      ]);

      setupEventsStore([
        createEventsStatus('kraken', 'Kraken', HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED),
      ]);

      const historyStore = useHistoryStore();
      historyStore.setUndecodedTransactionsStatus(createDecodingStatus('eth', 100, 100));

      const { overallProgress } = useSyncProgress();
      // All activities at 100%
      expect(get(overallProgress)).toBe(100);
    });
  });

  describe('counts', () => {
    it('should count chains correctly', () => {
      setupTxStore([
        createEvmTxStatus('0x111', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
        createEvmTxStatus('0x222', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
        createEvmTxStatus('0x333', 'optimism', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      ]);

      const { totalChains, completedChains } = useSyncProgress();
      expect(get(totalChains)).toBe(2);
      expect(get(completedChains)).toBe(1); // eth is complete
    });

    it('should count locations correctly', () => {
      setupEventsStore([
        createEventsStatus('kraken', 'Kraken', HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED),
        createEventsStatus('binance', 'Binance', HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE),
      ]);

      const { totalLocations, completedLocations } = useSyncProgress();
      expect(get(totalLocations)).toBe(2);
      expect(get(completedLocations)).toBe(1);
    });

    it('should count accounts correctly', () => {
      setupTxStore([
        createEvmTxStatus('0x111', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
        createEvmTxStatus('0x222', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
        createEvmTxStatus('0x333', 'optimism', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
      ]);

      const { totalAccounts, completedAccounts } = useSyncProgress();
      expect(get(totalAccounts)).toBe(3);
      expect(get(completedAccounts)).toBe(2);
    });

    it('should count unique addresses correctly', () => {
      setupTxStore([
        createEvmTxStatus('0x111', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
        createEvmTxStatus('0x111', 'optimism', TransactionsQueryStatus.QUERYING_TRANSACTIONS), // Same address, different chain
        createEvmTxStatus('0x222', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
      ]);

      const { uniqueAddresses, totalAccounts } = useSyncProgress();
      expect(get(totalAccounts)).toBe(3);
      expect(get(uniqueAddresses)).toBe(2); // 0x111 and 0x222
    });
  });

  describe('canDismiss', () => {
    it('should be false when syncing', () => {
      setupTxStore([
        createEvmTxStatus('0x123', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      ]);

      const { canDismiss } = useSyncProgress();
      expect(get(canDismiss)).toBe(false);
    });

    it('should be true when complete', () => {
      setupTxStore([
        createEvmTxStatus('0x123', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
      ]);

      const { canDismiss } = useSyncProgress();
      expect(get(canDismiss)).toBe(true);
    });
  });

  describe('state object', () => {
    it('should aggregate all computed values', () => {
      setupTxStore([
        createEvmTxStatus('0x123', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      ]);

      const { state } = useSyncProgress();
      const stateValue = get(state);

      expect(stateValue).toMatchObject({
        canDismiss: false,
        completedAccounts: 0,
        completedChains: 0,
        completedLocations: 0,
        isActive: true,
        phase: SyncPhase.SYNCING,
        totalAccounts: 1,
        totalChains: 1,
        totalLocations: 0,
      });
      expect(stateValue.chains).toHaveLength(1);
      expect(stateValue.locations).toHaveLength(0);
      expect(stateValue.decoding).toHaveLength(0);
      expect(stateValue.protocolCache).toHaveLength(0);
    });
  });
});
