import { submitRefresh } from '@test/utils/history-refresh';
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
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';
import { LocationStatus, SyncPhase } from './types';
import { useSyncProgress } from './use-sync-progress';
import { SyncWarningSource, useSyncWarningsStore } from './use-sync-warnings-store';

describe('useSyncProgress', () => {
  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
    // The orchestrator is a shared singleton, so its records outlive a test without this.
    useTaskOrchestrator().reset();
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

    it('should return SYNCING while any part of the refresh is still in flight', async () => {
      await submitRefresh({ eth: { '0x123': 'running' } });

      const { phase } = useSyncProgress();
      expect(get(phase)).toBe(SyncPhase.SYNCING);
    });

    it('should return COMPLETE once every activity has settled', async () => {
      await submitRefresh({ eth: { '0x123': 'complete' } });

      const { phase } = useSyncProgress();
      expect(get(phase)).toBe(SyncPhase.COMPLETE);
    });

    /** A failure is a settled outcome, so it must not leave the panel reading as still working. */
    it('should complete when an account failed rather than sitting short of the end', async () => {
      await submitRefresh({ eth: { '0x123': 'complete', '0x456': 'failed' } });

      const { overallProgress, phase } = useSyncProgress();
      expect(get(phase)).toBe(SyncPhase.COMPLETE);
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

    it('should be true while the refresh has work in flight', async () => {
      await submitRefresh({ eth: { '0x123': 'running' } });

      const { isActive } = useSyncProgress();
      expect(get(isActive)).toBe(true);
    });

    /**
     * The ledger has no notion of a warning, so this clause is deliberately not derived from it:
     * without it the panel would vanish as the run ends, taking the failures it exists to report.
     */
    it('should stay true after the work stops when there are warnings to show', async () => {
      await submitRefresh({ eth: { '0x123': 'complete' } });
      useSyncWarningsStore().addWarning({
        key: 'eth:0x123',
        message: 'the query failed',
        source: SyncWarningSource.TRANSACTIONS,
      });

      const { isActive } = useSyncProgress();
      expect(get(isActive)).toBe(true);
    });

    it('should be false once the work has settled and nothing warned', async () => {
      await submitRefresh({ eth: { '0x123': 'complete' } });

      const { isActive } = useSyncProgress();
      expect(get(isActive)).toBe(false);
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

    it('should count settled leaves over declared leaves', async () => {
      await submitRefresh({ eth: { '0x123': 'complete', '0x456': 'running' } });

      const { overallProgress } = useSyncProgress();
      expect(get(overallProgress)).toBe(50);
    });

    /**
     * The unit is the leaf, not the chain. Weighting whole chains equally would make one settled
     * account worth more on a two-account chain than on a ten-account one.
     */
    it('should weight every account equally, whichever chain it sits on', async () => {
      await submitRefresh({
        eth: { '0x1': 'complete', '0x2': 'running', '0x3': 'running' },
        gnosis: { '0xa': 'complete' },
      });

      const { overallProgress } = useSyncProgress();
      expect(get(overallProgress)).toBe(50);
    });

    /** A chain settles when its accounts do, so counting it too would double-count that work. */
    it('should not count the chain and umbrella rows as units of work', async () => {
      await submitRefresh({ eth: { '0x123': 'complete' } });

      const { overallProgress } = useSyncProgress();
      expect(get(overallProgress)).toBe(100);
    });

    it('should treat a cancelled leaf as settled, since nothing more will happen to it', async () => {
      await submitRefresh({ eth: { '0x123': 'complete', '0x456': 'cancelled' } });

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

    /**
     * The bar counts what the flow declared, and a disabled chain is never declared:
     * `getAccountsByChainType` filters at the source funnel every account getter reads through, so
     * the exclusion happens while the refresh scope resolves, before anything is submitted.
     * Re-filtering here would be a second implementation of the same rule, free to disagree.
     */
    it('should not re-filter disabled chains, which never reach the ledger to begin with', async () => {
      await submitRefresh({ eth: { '0x111': 'complete', '0x222': 'running' } });
      expect(get(useSyncProgress().overallProgress)).toBe(50);

      disableChains({ [SETTING_POLYGON]: [] });

      expect(get(useSyncProgress().overallProgress)).toBe(50);
    });

    it('should exclude a disabled chain from the chain and account counts', () => {
      setupTxStore([
        createEvmTxStatus('0x111', WIRE_ETH, TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
        createEvmTxStatus('0x222', WIRE_POLYGON, TransactionsQueryStatus.QUERYING_TRANSACTIONS),
        createEvmTxStatus('0x333', WIRE_POLYGON, TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      ]);
      disableChains({ [SETTING_POLYGON]: [] });

      const { chains, completedChains, totalChains } = useSyncProgress();
      expect(get(totalChains)).toBe(1);
      expect(get(completedChains)).toBe(1);
      expect(get(chains).map(chain => chain.chain)).toEqual([SETTING_ETH]);
    });

    it('should exclude a single disabled address, whatever its casing, but keep the rest of its chain', () => {
      setupTxStore([
        createEvmTxStatus('0x111', WIRE_ETH, TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
        createEvmTxStatus(WIRE_ADDRESS, WIRE_ETH, TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      ]);

      expect(WIRE_ADDRESS.toLowerCase()).toBe(SETTING_ADDRESS);
      disableChains({ [SETTING_ETH]: [SETTING_ADDRESS] });

      const { chains, totalChains } = useSyncProgress();
      expect(get(totalChains)).toBe(1);
      expect(get(chains)[0].addresses.map(a => a.address)).toEqual(['0x111']);
    });

    it('should exclude a disabled chain from the decoding list', () => {
      const decodingStatusStore = useDecodingStatusStore();
      decodingStatusStore.resetDecodingSyncProgress();
      decodingStatusStore.setUndecodedTransactionsStatus(createDecodingStatus('eth', 100, 100));
      decodingStatusStore.setUndecodedTransactionsStatus(createDecodingStatus('polygon_pos', 100, 0));

      disableChains({ polygon_pos: [] });

      expect(get(useSyncProgress().decoding).map(item => item.chain)).toEqual(['eth']);
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
  });

  describe('cancellation handling', () => {
    it('should become COMPLETE when every item was cancelled', async () => {
      await submitRefresh({ eth: { '0x123': 'cancelled', '0x456': 'cancelled' } });

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

    it('should treat a cancelled decode as done for phase calculation', async () => {
      await submitRefresh({ eth: { '0x123': 'complete' } }, { eth: 'cancelled' });

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

    /**
     * A decode is one leaf among the accounts, not a weighted third of the bar. Under the old
     * split it carried 20% whatever the shape of the run, so one cancelled decode moved the bar
     * as much as every account on a ten-account chain.
     */
    it('should count a decode as one leaf rather than a weighted share', async () => {
      await submitRefresh({ eth: { '0x123': 'complete', '0x456': 'running' } }, { eth: 'cancelled' });

      const { overallProgress } = useSyncProgress();
      expect(get(overallProgress)).toBe(67);
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

    it('should be true when complete', async () => {
      await submitRefresh({ eth: { '0x123': 'complete' } });

      const { canDismiss } = useSyncProgress();
      expect(get(canDismiss)).toBe(true);
    });
  });
});
