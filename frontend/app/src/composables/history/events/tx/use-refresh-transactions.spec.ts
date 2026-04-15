import type { RefreshTransactionsParams } from './types';
import type { Exchange } from '@/modules/balances/types/exchanges';
import type { ChainAddress } from '@/modules/history/events/event-payloads';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Status } from '@/modules/common/status';
import { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import { useHistoryRefreshStateStore } from '@/store/history/refresh-state';
import { useRefreshTransactions } from './use-refresh-transactions';

const mockOnHistoryStarted = vi.fn();
const mockOnHistoryFinished = vi.fn();

vi.mock('@/composables/session/use-scheduler-state', () => ({
  useSchedulerState: vi.fn(() => ({
    onHistoryStarted: mockOnHistoryStarted,
    onHistoryFinished: mockOnHistoryFinished,
  })),
}));

const mockEvmAccounts: ChainAddress[] = [
  { address: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c', chain: 'eth' },
  { address: '0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199', chain: 'optimism' },
];

const mockBitcoinAccounts: ChainAddress[] = [
  { address: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh', chain: 'btc' },
];

const mockExchanges: Exchange[] = [
  { location: 'kraken', name: 'Kraken1' },
  { location: 'binance', name: 'Binance1' },
];

// Mock stores and composables
const mockTxQueryStatusStore = {
  initializeQueryStatus: vi.fn(),
  resetQueryStatus: vi.fn(),
  stopSyncing: vi.fn(),
};

const mockEventsQueryStatusStore = {
  initializeQueryStatus: vi.fn(),
  resetQueryStatus: vi.fn(),
  stopSyncing: vi.fn(),
};

const mockHistoryTransactionAccounts = {
  getAllAccounts: vi.fn(() => [...mockEvmAccounts, ...mockBitcoinAccounts]),
};

const mockStatusUpdater = {
  fetchDisabled: vi.fn(() => false),
  getStatus: vi.fn(() => Status.NONE),
  isFirstLoad: vi.fn(() => true),
  loading: vi.fn(() => false),
  resetStatus: vi.fn(),
  setStatus: vi.fn(),
};

const mockHistoryTransactionDecoding = {
  fetchUndecodedTransactionsBreakdown: vi.fn().mockResolvedValue(undefined),
  fetchUndecodedTransactionsStatus: vi.fn().mockResolvedValue(undefined),
};

const mockDecodingStatusStore = {
  resetDecodingSyncProgress: vi.fn(),
  resetUndecodedTransactionsStatus: vi.fn(),
  stopDecodingSyncProgress: vi.fn(),
};

const mockTransactionSync = {
  syncTransactionsByChains: vi.fn().mockResolvedValue(undefined),
  waitForDecoding: vi.fn().mockResolvedValue(undefined),
};

const mockSupportedChains = {
  isDecodableChains: vi.fn((chain: string) => ['eth', 'optimism', 'polygon_pos', 'solana'].includes(chain)),
};

const mockRefreshHandlers = {
  queryAllExchangeEvents: vi.fn().mockResolvedValue(undefined),
  queryOnlineEvent: vi.fn().mockResolvedValue(undefined),
};

const mockExchangeData = {
  isSameExchange: (a: Exchange, b: Exchange): boolean => a.location === b.location && a.name === b.name,
  syncingExchanges: ref<Exchange[]>(mockExchanges),
};

vi.mock('./use-history-transaction-accounts', () => ({
  useHistoryTransactionAccounts: vi.fn(() => mockHistoryTransactionAccounts),
}));

vi.mock(import('@/composables/status'), async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useStatusUpdater: vi.fn(() => mockStatusUpdater),
  };
});

vi.mock('./decoding', () => ({
  useHistoryTransactionDecoding: vi.fn(() => mockHistoryTransactionDecoding),
}));

vi.mock('@/modules/history/use-decoding-status-store', () => ({
  useDecodingStatusStore: vi.fn(() => mockDecodingStatusStore),
}));

vi.mock('./use-transaction-sync', () => ({
  useTransactionSync: vi.fn(() => mockTransactionSync),
}));

vi.mock('@/composables/info/chains', () => ({
  useSupportedChains: vi.fn(() => mockSupportedChains),
}));

vi.mock('./refresh-handlers', () => ({
  useRefreshHandlers: vi.fn(() => mockRefreshHandlers),
}));

vi.mock('@/modules/balances/exchanges/use-exchange-data', () => ({
  useExchangeData: vi.fn(() => mockExchangeData),
}));

vi.mock('@/store/history/query-status/tx-query-status', () => ({
  useTxQueryStatusStore: vi.fn(() => mockTxQueryStatusStore),
}));

vi.mock('@/store/history/query-status/events-query-status', () => ({
  useEventsQueryStatusStore: vi.fn(() => mockEventsQueryStatusStore),
}));

describe('useRefreshTransactions', () => {
  let scope: ReturnType<typeof effectScope>;

  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
    scope = effectScope();

    // Reset the refresh state store
    const refreshStateStore = useHistoryRefreshStateStore();
    refreshStateStore.reset();

    vi.clearAllMocks();
    mockStatusUpdater.fetchDisabled.mockReturnValue(false);
    mockStatusUpdater.isFirstLoad.mockReturnValue(true);

    // Reset mock return values to defaults
    mockHistoryTransactionAccounts.getAllAccounts.mockReturnValue([...mockEvmAccounts, ...mockBitcoinAccounts]);
    set(mockExchangeData.syncingExchanges, mockExchanges);
  });

  afterEach(() => {
    scope.stop();
  });

  describe('basic refresh flow', () => {
    it('should perform full refresh when called without parameters', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockStatusUpdater.setStatus).toHaveBeenCalledWith(Status.LOADING);
      expect(mockTxQueryStatusStore.initializeQueryStatus).toHaveBeenCalled();
      expect(mockDecodingStatusStore.resetUndecodedTransactionsStatus).toHaveBeenCalled();
      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalled();
      expect(mockRefreshHandlers.queryAllExchangeEvents).toHaveBeenCalled();
      expect(mockStatusUpdater.setStatus).toHaveBeenCalledWith(Status.LOADED);
    });

    it('should skip refresh when fetchDisabled returns true and no new accounts', async () => {
      mockStatusUpdater.fetchDisabled.mockReturnValue(true);

      // First, perform a refresh to mark all accounts/exchanges as refreshed
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      mockStatusUpdater.fetchDisabled.mockReturnValue(false);
      await refreshTransactions();

      // Reset mocks and set fetchDisabled to true
      vi.clearAllMocks();
      mockStatusUpdater.fetchDisabled.mockReturnValue(true);

      // Now refresh again - should be skipped since no new accounts/exchanges
      await refreshTransactions();

      expect(mockStatusUpdater.setStatus).not.toHaveBeenCalled();
      expect(mockTransactionSync.syncTransactionsByChains).not.toHaveBeenCalled();
    });

    it('should set LOADING status on first load', async () => {
      mockStatusUpdater.isFirstLoad.mockReturnValue(true);
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockStatusUpdater.setStatus).toHaveBeenCalledWith(Status.LOADING);
    });

    it('should set REFRESHING status on subsequent loads', async () => {
      mockStatusUpdater.isFirstLoad.mockReturnValue(false);
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockStatusUpdater.setStatus).toHaveBeenCalledWith(Status.REFRESHING);
    });
  });

  describe('account-specific refresh', () => {
    it('should refresh only specified accounts', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      const specificAccounts = [mockEvmAccounts[0]];

      await refreshTransactions({
        payload: { accounts: specificAccounts },
        userInitiated: true, // Ensure it bypasses any "already refreshed" logic
      });

      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalledWith(
        specificAccounts,
        true, // shouldShowSyncProgress is true because isFirstLoad() returns true
      );
    });

    it('should not query exchanges when only accounts are specified', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions({
        payload: { accounts: mockEvmAccounts },
      });

      expect(mockRefreshHandlers.queryAllExchangeEvents).not.toHaveBeenCalled();
      expect(mockEventsQueryStatusStore.resetQueryStatus).toHaveBeenCalled();
    });
  });

  describe('exchange refresh', () => {
    it('should refresh exchanges when exchanges are specified', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions({
        payload: { exchanges: mockExchanges },
      });

      expect(mockEventsQueryStatusStore.initializeQueryStatus).toHaveBeenCalledWith(mockExchanges);
      expect(mockRefreshHandlers.queryAllExchangeEvents).toHaveBeenCalledWith(mockExchanges);
    });

    it('should refresh all connected exchanges in full refresh', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockRefreshHandlers.queryAllExchangeEvents).toHaveBeenCalledWith(mockExchanges);
      expect(mockEventsQueryStatusStore.initializeQueryStatus).toHaveBeenCalled();
    });
  });

  describe('new account detection', () => {
    it('should bypass fetchDisabled when new accounts are detected', async () => {
      mockStatusUpdater.fetchDisabled.mockReturnValue(true);
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      // Even with fetchDisabled true, should proceed due to new accounts
      expect(mockStatusUpdater.setStatus).toHaveBeenCalledWith(Status.LOADING);
    });
  });

  describe('new exchange detection', () => {
    it('should bypass fetchDisabled when new exchanges are detected', async () => {
      mockStatusUpdater.fetchDisabled.mockReturnValue(true);
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      // Even with fetchDisabled true, should proceed due to new exchanges
      expect(mockStatusUpdater.setStatus).toHaveBeenCalledWith(Status.LOADING);
    });
  });

  describe('concurrent refresh handling', () => {
    it('should add new accounts to pending when refresh is running', async () => {
      vi.useFakeTimers();

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      const firstRefresh = refreshTransactions();

      // Trigger another refresh while first is running
      await refreshTransactions({
        payload: { accounts: [mockEvmAccounts[0]] },
      });

      await firstRefresh;

      await vi.advanceTimersByTimeAsync(150);

      // Should be called 2 times: first refresh (all accounts) + pending refresh (single account)
      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalledTimes(2);

      vi.useRealTimers();
    });
  });

  describe('chain filtering', () => {
    it('should filter accounts by specified chains', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions({
        chains: ['eth'],
      });

      expect(mockHistoryTransactionAccounts.getAllAccounts).toHaveBeenCalledWith(['eth']);
    });
  });

  describe('disableEvmEvents parameter', () => {
    it('should execute only ETH_WITHDRAWALS and BLOCK_PRODUCTIONS queries when disableEvmEvents is true', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions({
        disableEvmEvents: true,
        payload: {
          accounts: mockEvmAccounts,
        },
      });

      expect(mockRefreshHandlers.queryOnlineEvent).toHaveBeenCalledWith(
        OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
      );
      expect(mockRefreshHandlers.queryOnlineEvent).toHaveBeenCalledWith(
        OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS,
      );
      expect(mockRefreshHandlers.queryOnlineEvent).toHaveBeenCalledTimes(2);
    });

    it('should execute custom queries when disableEvmEvents is false', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions({
        disableEvmEvents: false,
        payload: {
          accounts: mockEvmAccounts,
          queries: [OnlineHistoryEventsQueryType.ETH_WITHDRAWALS],
        },
      });

      expect(mockRefreshHandlers.queryOnlineEvent).toHaveBeenCalledWith(
        OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
      );
      expect(mockRefreshHandlers.queryOnlineEvent).toHaveBeenCalledTimes(1);
    });
  });

  describe('online queries', () => {
    it('should execute ETH_WITHDRAWALS and BLOCK_PRODUCTIONS queries on full refresh', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockRefreshHandlers.queryOnlineEvent).toHaveBeenCalledWith(
        OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
      );
      expect(mockRefreshHandlers.queryOnlineEvent).toHaveBeenCalledWith(
        OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS,
      );
    });

    it('should execute custom queries when specified', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions({
        payload: {
          queries: [OnlineHistoryEventsQueryType.ETH_WITHDRAWALS],
        },
      });

      expect(mockRefreshHandlers.queryOnlineEvent).toHaveBeenCalledWith(
        OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
      );
      expect(mockRefreshHandlers.queryOnlineEvent).toHaveBeenCalledTimes(1);
    });
  });

  describe('error handling', () => {
    it('should handle errors gracefully and reset status', async () => {
      mockTransactionSync.syncTransactionsByChains.mockRejectedValue(new Error('Sync failed'));
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockStatusUpdater.setStatus).toHaveBeenCalledWith(Status.LOADED);
    });

    it('should continue with other operations when one fails', async () => {
      mockTransactionSync.syncTransactionsByChains.mockRejectedValue(new Error('Sync failed'));
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockHistoryTransactionDecoding.fetchUndecodedTransactionsBreakdown).toHaveBeenCalled();
    });

    it('should call resetStatus when executeOperations throws', async () => {
      mockHistoryTransactionDecoding.fetchUndecodedTransactionsStatus.mockRejectedValueOnce(
        new Error('Fatal error'),
      );
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockStatusUpdater.resetStatus).toHaveBeenCalled();
    });

    it('should still call finishRefresh and cleanup on error', async () => {
      mockHistoryTransactionDecoding.fetchUndecodedTransactionsStatus.mockRejectedValueOnce(
        new Error('Fatal error'),
      );
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockTxQueryStatusStore.stopSyncing).toHaveBeenCalled();
      expect(mockEventsQueryStatusStore.stopSyncing).toHaveBeenCalled();
      expect(mockDecodingStatusStore.stopDecodingSyncProgress).toHaveBeenCalled();
    });
  });

  describe('transaction chain type sync', () => {
    it('should sync EVM transactions', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalledWith(
        expect.arrayContaining([
          expect.objectContaining({ chain: 'eth' }),
          expect.objectContaining({ chain: 'optimism' }),
        ]),
        true, // shouldShowSyncProgress is true because isFirstLoad() returns true
      );
    });

    it('should sync Bitcoin transactions', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalledWith(
        expect.arrayContaining([
          expect.objectContaining({ chain: 'btc' }),
        ]),
        true, // shouldShowSyncProgress is true because isFirstLoad() returns true
      );
    });

    it('should not sync transactions for empty account types', async () => {
      mockHistoryTransactionAccounts.getAllAccounts.mockReturnValue([]);

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockTransactionSync.syncTransactionsByChains).not.toHaveBeenCalled();
    });
  });

  describe('query status management', () => {
    it('should initialize query status for EVM accounts', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockTxQueryStatusStore.initializeQueryStatus).toHaveBeenCalledWith(mockEvmAccounts);
    });

    it('should reset query status when no accounts to refresh', async () => {
      mockHistoryTransactionAccounts.getAllAccounts.mockReturnValue([]);

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions({
        payload: { accounts: [], exchanges: [] },
      });

      expect(mockTxQueryStatusStore.resetQueryStatus).toHaveBeenCalled();
    });
  });

  describe('userInitiated parameter', () => {
    it('should pass userInitiated to fetchDisabled check', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions({ userInitiated: true });

      expect(mockStatusUpdater.fetchDisabled).toHaveBeenCalledWith(true);
    });

    it('should default userInitiated to false', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockStatusUpdater.fetchDisabled).toHaveBeenCalledWith(false);
    });
  });

  describe('scheduler state hooks', () => {
    it('should call onHistoryStarted when refresh starts with accounts', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockOnHistoryStarted).toHaveBeenCalledTimes(1);
    });

    it('should call onHistoryFinished when refresh completes', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockOnHistoryFinished).toHaveBeenCalledTimes(1);
    });

    it('should call onHistoryFinished even when errors occur', async () => {
      mockTransactionSync.syncTransactionsByChains.mockRejectedValue(new Error('Sync failed'));
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockOnHistoryFinished).toHaveBeenCalledTimes(1);
    });

    it('should not call onHistoryStarted when no accounts or exchanges to refresh', async () => {
      mockHistoryTransactionAccounts.getAllAccounts.mockReturnValue([]);
      set(mockExchangeData.syncingExchanges, []);

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions({
        payload: { accounts: [], exchanges: [] },
      });

      expect(mockOnHistoryStarted).not.toHaveBeenCalled();
    });

    it('should call onHistoryStarted before sync operations', async () => {
      const callOrder: string[] = [];

      mockOnHistoryStarted.mockImplementation(() => {
        callOrder.push('onHistoryStarted');
      });
      mockTransactionSync.syncTransactionsByChains.mockImplementation(async () => {
        callOrder.push('syncTransactionsByChains');
      });

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(callOrder.indexOf('onHistoryStarted')).toBeLessThan(callOrder.indexOf('syncTransactionsByChains'));
    });

    it('should wait for decoding to complete before stopping decoding sync progress', async () => {
      const callOrder: string[] = [];

      mockTransactionSync.waitForDecoding.mockImplementation(async () => {
        callOrder.push('waitForDecoding');
      });
      mockDecodingStatusStore.stopDecodingSyncProgress.mockImplementation(() => {
        callOrder.push('stopDecodingSyncProgress');
      });

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockTransactionSync.waitForDecoding).toHaveBeenCalledTimes(1);
      expect(callOrder.indexOf('waitForDecoding')).toBeLessThan(callOrder.indexOf('stopDecodingSyncProgress'));
    });

    it('should call onHistoryFinished after all operations complete', async () => {
      const callOrder: string[] = [];

      mockTransactionSync.syncTransactionsByChains.mockImplementation(async () => {
        callOrder.push('syncTransactionsByChains');
      });
      mockOnHistoryFinished.mockImplementation(() => {
        callOrder.push('onHistoryFinished');
      });

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(callOrder.indexOf('syncTransactionsByChains')).toBeLessThan(callOrder.indexOf('onHistoryFinished'));
    });
  });

  describe('exchange filtering', () => {
    it('should filter out exchanges not in syncingExchanges', async () => {
      const unknownExchange: Exchange = { location: 'unknown_exchange', name: 'Unknown' };
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions({
        payload: { exchanges: [mockExchanges[0], unknownExchange] },
      });

      // Only the known exchange should be passed (filtered against syncingExchanges)
      expect(mockRefreshHandlers.queryAllExchangeEvents).toHaveBeenCalledWith([mockExchanges[0]]);
    });
  });

  describe('pending drain', () => {
    it('should drain pending exchanges after refresh completes', async () => {
      vi.useFakeTimers();

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      const firstRefresh = refreshTransactions();

      // Queue pending exchanges while first refresh is running
      await refreshTransactions({
        payload: { exchanges: mockExchanges },
      });

      await firstRefresh;

      await vi.advanceTimersByTimeAsync(150);

      // queryAllExchangeEvents called in first refresh + pending drain
      expect(mockRefreshHandlers.queryAllExchangeEvents).toHaveBeenCalledTimes(2);

      vi.useRealTimers();
    });
  });

  describe('sync progress', () => {
    it('should not initialize query status when not first load and no novel items', async () => {
      mockStatusUpdater.isFirstLoad.mockReturnValue(false);

      // First refresh to mark all accounts as known
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      await refreshTransactions({ userInitiated: true });

      vi.clearAllMocks();
      mockStatusUpdater.isFirstLoad.mockReturnValue(false);

      // Second refresh — not first load, no novel items
      await refreshTransactions({ userInitiated: true });

      expect(mockTxQueryStatusStore.initializeQueryStatus).not.toHaveBeenCalled();
      expect(mockDecodingStatusStore.resetUndecodedTransactionsStatus).not.toHaveBeenCalled();
    });
  });

  describe('full refresh with no new accounts', () => {
    it('should not refresh accounts when all accounts are already known and not user initiated', async () => {
      // First refresh to mark all accounts as known
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      await refreshTransactions();

      vi.clearAllMocks();
      mockStatusUpdater.fetchDisabled.mockReturnValue(false);

      // Second refresh — all accounts known, not user initiated
      // fetchDisabled returns false so it proceeds, but no new accounts
      await refreshTransactions();

      // No accounts to sync since none are new and not userInitiated
      expect(mockTransactionSync.syncTransactionsByChains).not.toHaveBeenCalled();
    });
  });

  describe('undecoded transactions', () => {
    it('should queue fetchUndecodedTransactionsBreakdown after operations complete', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockHistoryTransactionDecoding.fetchUndecodedTransactionsBreakdown).toHaveBeenCalled();
    });

    it('should queue fetchUndecodedTransactionsStatus for decodable accounts', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      // Called once during executeOperations + once queued for final status
      expect(mockHistoryTransactionDecoding.fetchUndecodedTransactionsStatus).toHaveBeenCalled();
    });

    it('should not queue final fetchUndecodedTransactionsStatus when no decodable accounts', async () => {
      // Return only non-decodable accounts
      mockHistoryTransactionAccounts.getAllAccounts.mockReturnValue(mockBitcoinAccounts);

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      // fetchUndecodedTransactionsStatus should still be called once for fullRefresh
      // but NOT queued again for the final status check
      expect(mockHistoryTransactionDecoding.fetchUndecodedTransactionsStatus).toHaveBeenCalledTimes(1);
    });
  });

  describe('scope cleanup', () => {
    it('should clear pending timeout when scope is disposed', async () => {
      vi.useFakeTimers();

      const scope = effectScope();
      let refreshFn: ((params?: RefreshTransactionsParams) => Promise<void>) | undefined;

      scope.run(() => {
        const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
        refreshFn = refreshTransactions;
      });

      // Start a refresh and trigger a concurrent one to create pending items
      const firstRefresh = refreshFn!();
      await refreshFn!({ payload: { accounts: [mockEvmAccounts[0]] } });
      await firstRefresh;

      // Dispose the scope before the timeout fires
      scope.stop();

      vi.clearAllMocks();
      await vi.advanceTimersByTimeAsync(150);

      // The pending drain should NOT have fired
      expect(mockTransactionSync.syncTransactionsByChains).not.toHaveBeenCalled();

      vi.useRealTimers();
    });
  });
});
