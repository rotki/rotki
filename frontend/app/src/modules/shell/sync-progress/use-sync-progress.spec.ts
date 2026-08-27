import { beforeEach, describe, expect, it } from 'vitest';
import {
  type EvmUnDecodedTransactionsData,
  type HistoryEventsQueryData,
  HistoryEventsQueryStatus,
  type ProtocolCacheUpdatesData,
  TransactionsQueryStatus,
  type UnifiedTransactionStatusData,
} from '@/modules/core/messaging/types';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';
import { useEventsQueryStatusStore } from '@/modules/history/use-events-query-status-store';
import { useProtocolCacheStatusStore } from '@/modules/history/use-protocol-cache-status-store';
import { useTxQueryStatusStore } from '@/modules/history/use-tx-query-status-store';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { LocationStatus, SyncPhase } from './types';
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
    period: [0, 500],
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
    const addresses = statuses
      .filter((s): s is UnifiedTransactionStatusData & { address: string } => 'address' in s)
      .map(s => ({ address: s.address, chain: s.chain, subtype: s.subtype }));
    txStore.initializeQueryStatus(addresses);
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

    it('should complete when a chain failed rather than sitting short of the end', () => {
      setupTxStore([
        createEvmTxStatus('0x123', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
        createEvmTxStatus('0x456', 'gnosis', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      ]);
      useTxQueryStatusStore().markAddressFailed({ address: '0x456', chain: 'gnosis' });

      setupEventsStore([
        createEventsStatus('kraken', 'Kraken', HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED),
      ]);

      const { completedChains, overallProgress, phase } = useSyncProgress();
      expect(get(phase)).toBe(SyncPhase.COMPLETE);
      expect(get(completedChains)).toBe(2);
      expect(get(overallProgress)).toBe(100);
    });

    it('should report warnings, with an entry each, when a chain failed', () => {
      setupTxStore([
        createEvmTxStatus('0x456', 'gnosis', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      ]);
      useTxQueryStatusStore().markAddressFailed({ address: '0x456', chain: 'gnosis' });

      const { hasWarnings, warnings } = useSyncProgress();
      expect(get(hasWarnings)).toBe(true);
      expect(get(warnings)).toHaveLength(1);
      expect(get(warnings)[0].key).toBe('gnosis');
      expect(get(warnings)[0].message).toBeTruthy();
    });

    it('should not report warnings when everything succeeded', () => {
      setupTxStore([
        createEvmTxStatus('0x123', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
      ]);

      const { hasWarnings } = useSyncProgress();
      expect(get(hasWarnings)).toBe(false);
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
      const decodingStatusStore = useDecodingStatusStore();
      decodingStatusStore.resetDecodingSyncProgress();
      decodingStatusStore.setUndecodedTransactionsStatus(createDecodingStatus('eth', 100, 50));

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
      const decodingStatusStore = useDecodingStatusStore();
      decodingStatusStore.resetDecodingSyncProgress();
      decodingStatusStore.setUndecodedTransactionsStatus(createDecodingStatus('eth', 100, 50));

      const { decoding } = useSyncProgress();
      const decodingValue = get(decoding);

      expect(decodingValue).toHaveLength(1);
      expect(decodingValue[0].chain).toBe('eth');
      expect(decodingValue[0].total).toBe(100);
      expect(decodingValue[0].processed).toBe(50);
      expect(decodingValue[0].progress).toBe(50);
    });

    it('should not update sync progress after stopDecodingSyncProgress is called', () => {
      const decodingStatusStore = useDecodingStatusStore();
      decodingStatusStore.resetDecodingSyncProgress();
      decodingStatusStore.setUndecodedTransactionsStatus(createDecodingStatus('eth', 100, 50));

      decodingStatusStore.stopDecodingSyncProgress();
      decodingStatusStore.setUndecodedTransactionsStatus(createDecodingStatus('eth', 100, 100));

      const { decoding } = useSyncProgress();
      const decodingValue = get(decoding);

      expect(decodingValue).toHaveLength(1);
      expect(decodingValue[0].processed).toBe(50);
    });

    it('should continue updating sync progress while decodingSyncing is true', () => {
      const decodingStatusStore = useDecodingStatusStore();
      decodingStatusStore.resetDecodingSyncProgress();
      decodingStatusStore.setUndecodedTransactionsStatus(createDecodingStatus('eth', 100, 0));
      decodingStatusStore.setUndecodedTransactionsStatus(createDecodingStatus('eth', 100, 50));
      decodingStatusStore.setUndecodedTransactionsStatus(createDecodingStatus('eth', 100, 100));

      const { decoding } = useSyncProgress();
      const decodingValue = get(decoding);

      expect(decodingValue).toHaveLength(1);
      expect(decodingValue[0].processed).toBe(100);
    });

    it('should filter out chains with total 0', () => {
      const decodingStatusStore = useDecodingStatusStore();
      decodingStatusStore.resetDecodingSyncProgress();
      decodingStatusStore.setUndecodedTransactionsStatus(createDecodingStatus('eth', 0, 0));

      const { decoding } = useSyncProgress();
      const decodingValue = get(decoding);

      expect(decodingValue).toHaveLength(0);
    });
  });

  describe('protocol cache progress', () => {
    it('should calculate protocol cache progress correctly', () => {
      const protocolCacheStatusStore = useProtocolCacheStatusStore();
      protocolCacheStatusStore.setProtocolCacheStatus(createProtocolCacheStatus('eth', 'uniswap', 200, 100));

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
      expect(get(overallProgress)).toBe(50);
    });

    it('should calculate weighted progress with multiple activity types', () => {
      setupTxStore([
        createEvmTxStatus('0x123', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
      ]);

      setupEventsStore([
        createEventsStatus('kraken', 'Kraken', HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED),
      ]);

      const decodingStatusStore = useDecodingStatusStore();
      decodingStatusStore.resetDecodingSyncProgress();
      decodingStatusStore.setUndecodedTransactionsStatus(createDecodingStatus('eth', 100, 100));

      const { overallProgress } = useSyncProgress();
      expect(get(overallProgress)).toBe(100);
    });
  });

  describe('disabled chain queries', () => {
    const WIRE_ETH = 'ETH';
    const SETTING_ETH = 'eth';
    const WIRE_POLYGON = 'POLYGON_POS';
    const SETTING_POLYGON = 'polygon_pos';
    const WIRE_ADDRESS = '0xAbC';
    const SETTING_ADDRESS = '0xabc';

    function disableChains(value: Record<string, string[]>): void {
      const store = useSettingsRepo();
      store.updateGeneral({ ...store.general, disabledChainQueries: value });
    }

    it('should exclude a disabled chain from the transaction progress', () => {
      setupTxStore([
        createEvmTxStatus('0x111', WIRE_ETH, TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
        createEvmTxStatus('0x222', WIRE_POLYGON, TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      ]);

      expect(get(useSyncProgress().overallProgress)).toBe(50);

      disableChains({ [SETTING_POLYGON]: [] });
      expect(get(useSyncProgress().overallProgress)).toBe(100);
    });

    it('should exclude a disabled chain from the chain and account counts', () => {
      setupTxStore([
        createEvmTxStatus('0x111', WIRE_ETH, TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
        createEvmTxStatus('0x222', WIRE_POLYGON, TransactionsQueryStatus.QUERYING_TRANSACTIONS),
        createEvmTxStatus('0x333', WIRE_POLYGON, TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      ]);
      disableChains({ [SETTING_POLYGON]: [] });

      const { chains, completedChains, totalAccounts, totalChains } = useSyncProgress();
      expect(get(totalChains)).toBe(1);
      expect(get(completedChains)).toBe(1);
      expect(get(totalAccounts)).toBe(1);
      expect(get(chains).map(chain => chain.chain)).toEqual([SETTING_ETH]);
    });

    it('should exclude a single disabled address, whatever its casing, but keep the rest of its chain', () => {
      setupTxStore([
        createEvmTxStatus('0x111', WIRE_ETH, TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
        createEvmTxStatus(WIRE_ADDRESS, WIRE_ETH, TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      ]);

      expect(WIRE_ADDRESS.toLowerCase()).toBe(SETTING_ADDRESS);
      disableChains({ [SETTING_ETH]: [SETTING_ADDRESS] });

      const { chains, totalAccounts, totalChains } = useSyncProgress();
      expect(get(totalChains)).toBe(1);
      expect(get(totalAccounts)).toBe(1);
      expect(get(chains)[0].addresses.map(a => a.address)).toEqual(['0x111']);
    });

    it('should exclude a disabled chain from decoding, which owns the whole bar when nothing else runs', () => {
      const decodingStatusStore = useDecodingStatusStore();
      decodingStatusStore.resetDecodingSyncProgress();
      decodingStatusStore.setUndecodedTransactionsStatus(createDecodingStatus('eth', 100, 100));
      decodingStatusStore.setUndecodedTransactionsStatus(createDecodingStatus('polygon_pos', 100, 0));

      expect(get(useSyncProgress().overallProgress)).toBe(50);

      disableChains({ polygon_pos: [] });
      const { decoding, overallProgress } = useSyncProgress();
      expect(get(decoding).map(item => item.chain)).toEqual(['eth']);
      expect(get(overallProgress)).toBe(100);
    });

    it('should exclude a disabled chain from the protocol cache list', () => {
      const protocolCacheStatusStore = useProtocolCacheStatusStore();
      protocolCacheStatusStore.setProtocolCacheStatus(createProtocolCacheStatus('eth', 'uniswap', 200, 100));
      protocolCacheStatusStore.setProtocolCacheStatus(createProtocolCacheStatus('polygon_pos', 'uniswap', 200, 100));
      disableChains({ polygon_pos: [] });

      expect(get(useSyncProgress().protocolCache).map(item => item.chain)).toEqual(['eth']);
    });

    it('should not report a warning for a failed address on a disabled chain', () => {
      setupTxStore([
        createEvmTxStatus('0x456', 'gnosis', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      ]);
      useTxQueryStatusStore().markAddressFailed({ address: '0x456', chain: 'gnosis' });
      disableChains({ gnosis: [] });

      const { hasWarnings, warnings } = useSyncProgress();
      expect(get(warnings)).toHaveLength(0);
      expect(get(hasWarnings)).toBe(false);
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
      expect(get(completedChains)).toBe(1);
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
        createEvmTxStatus('0x111', 'optimism', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
        createEvmTxStatus('0x222', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
      ]);

      const { uniqueAddresses, totalAccounts } = useSyncProgress();
      expect(get(totalAccounts)).toBe(3);
      expect(get(uniqueAddresses)).toBe(2);
    });
  });

  describe('cancellation handling', () => {
    it('should become COMPLETE when all items are cancelled', () => {
      setupTxStore([
        createEvmTxStatus('0x123', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      ]);

      const txStore = useTxQueryStatusStore();
      txStore.markAddressCancelled({ address: '0x123', chain: 'eth' });

      setupEventsStore([
        createEventsStatus('kraken', 'Kraken', HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE),
      ]);

      const eventsStore = useEventsQueryStatusStore();
      eventsStore.markLocationCancelled({ location: 'kraken', name: 'Kraken' });

      const { phase } = useSyncProgress();
      expect(get(phase)).toBe(SyncPhase.COMPLETE);
    });

    it('should count cancelled locations in completedLocations', () => {
      setupEventsStore([
        createEventsStatus('kraken', 'Kraken', HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE),
        createEventsStatus('binance', 'Binance', HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED),
      ]);

      const eventsStore = useEventsQueryStatusStore();
      eventsStore.markLocationCancelled({ location: 'kraken', name: 'Kraken' });

      const { completedLocations, totalLocations } = useSyncProgress();
      expect(get(totalLocations)).toBe(2);
      expect(get(completedLocations)).toBe(2);
    });

    it('should count cancelled accounts in completedAccounts', () => {
      setupTxStore([
        createEvmTxStatus('0x123', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
        createEvmTxStatus('0x456', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
      ]);

      const txStore = useTxQueryStatusStore();
      txStore.markAddressCancelled({ address: '0x123', chain: 'eth' });

      const { completedAccounts, totalAccounts } = useSyncProgress();
      expect(get(totalAccounts)).toBe(2);
      expect(get(completedAccounts)).toBe(2);
    });

    it('should sort cancelled locations between pending and complete', () => {
      setupEventsStore([
        createEventsStatus('kraken', 'Kraken', HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED),
        createEventsStatus('binance', 'Binance', HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE),
        createEventsStatus('coinbase', 'Coinbase', HistoryEventsQueryStatus.QUERYING_EVENTS_STARTED),
      ]);

      const eventsStore = useEventsQueryStatusStore();
      eventsStore.markLocationCancelled({ location: 'coinbase', name: 'Coinbase' });

      const { locations } = useSyncProgress();
      const locationsValue = get(locations);

      expect(locationsValue[0].status).toBe(LocationStatus.QUERYING);
      expect(locationsValue[1].status).toBe(LocationStatus.CANCELLED);
      expect(locationsValue[2].status).toBe(LocationStatus.COMPLETE);
    });
  });

  describe('decoding cancellation handling', () => {
    it('should mark decoding as cancelled', () => {
      const decodingStatusStore = useDecodingStatusStore();
      decodingStatusStore.resetDecodingSyncProgress();
      decodingStatusStore.setUndecodedTransactionsStatus(createDecodingStatus('eth', 100, 50));
      decodingStatusStore.markDecodingCancelled('eth');

      const { decoding } = useSyncProgress();
      const decodingValue = get(decoding);

      expect(decodingValue).toHaveLength(1);
      expect(decodingValue[0].cancelled).toBe(true);
    });

    it('should treat cancelled decoding as done for phase calculation', () => {
      setupTxStore([
        createEvmTxStatus('0x123', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
      ]);

      const decodingStatusStore = useDecodingStatusStore();
      decodingStatusStore.resetDecodingSyncProgress();
      decodingStatusStore.setUndecodedTransactionsStatus(createDecodingStatus('eth', 100, 50));
      decodingStatusStore.markDecodingCancelled('eth');

      const { phase } = useSyncProgress();
      expect(get(phase)).toBe(SyncPhase.COMPLETE);
    });

    it('should include cancelled decoding in hasCancelled', () => {
      const decodingStatusStore = useDecodingStatusStore();
      decodingStatusStore.resetDecodingSyncProgress();
      decodingStatusStore.setUndecodedTransactionsStatus(createDecodingStatus('eth', 100, 50));
      decodingStatusStore.markDecodingCancelled('eth');

      const { hasCancelled, hasCancelledDecoding } = useSyncProgress();
      expect(get(hasCancelledDecoding)).toBe(true);
      expect(get(hasCancelled)).toBe(true);
    });

    it('should treat cancelled decoding as 100% for overall progress', () => {
      const decodingStatusStore = useDecodingStatusStore();
      decodingStatusStore.resetDecodingSyncProgress();
      decodingStatusStore.setUndecodedTransactionsStatus(createDecodingStatus('eth', 100, 50));
      decodingStatusStore.markDecodingCancelled('eth');

      const { overallProgress } = useSyncProgress();
      expect(get(overallProgress)).toBe(100);
    });
  });

  describe('protocol cache cancellation handling', () => {
    it('should mark protocol cache as cancelled', () => {
      const protocolCacheStatusStore = useProtocolCacheStatusStore();
      protocolCacheStatusStore.setProtocolCacheStatus(createProtocolCacheStatus('eth', 'uniswap', 200, 100));
      protocolCacheStatusStore.markAllProtocolCacheCancelled();

      const { protocolCache } = useSyncProgress();
      const protocolCacheValue = get(protocolCache);

      expect(protocolCacheValue).toHaveLength(1);
      expect(protocolCacheValue[0].cancelled).toBe(true);
    });

    it('should include cancelled protocol cache in hasCancelled', () => {
      const protocolCacheStatusStore = useProtocolCacheStatusStore();
      protocolCacheStatusStore.setProtocolCacheStatus(createProtocolCacheStatus('eth', 'uniswap', 200, 100));
      protocolCacheStatusStore.markAllProtocolCacheCancelled();

      const { hasCancelled, hasCancelledProtocolCache } = useSyncProgress();
      expect(get(hasCancelledProtocolCache)).toBe(true);
      expect(get(hasCancelled)).toBe(true);
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
