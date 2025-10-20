import type { Exchange } from '@/types/exchanges';
import type { ChainAddress } from '@/types/history/events';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useHistoryRefreshStateStore } from '@/store/history/refresh-state';
import { OnlineHistoryEventsQueryType } from '@/types/history/events/schemas';
import { Status } from '@/types/status';
import { useRefreshTransactions } from './use-refresh-transactions';

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
};

const mockEventsQueryStatusStore = {
  initializeQueryStatus: vi.fn(),
  resetQueryStatus: vi.fn(),
};

const mockHistoryTransactionAccounts = {
  getBitcoinAccounts: vi.fn(() => mockBitcoinAccounts),
  getEvmAccounts: vi.fn(() => mockEvmAccounts),
  getEvmLikeAccounts: vi.fn(() => []),
  getSolanaAccounts: vi.fn(() => []),
};

const mockStatusUpdater = {
  fetchDisabled: vi.fn(() => false),
  isFirstLoad: vi.fn(() => true),
  resetStatus: vi.fn(),
  setStatus: vi.fn(),
};

const mockHistoryTransactionDecoding = {
  fetchUndecodedTransactionsBreakdown: vi.fn().mockResolvedValue(undefined),
  fetchUndecodedTransactionsStatus: vi.fn().mockResolvedValue(undefined),
};

const mockHistoryStore = {
  resetUndecodedTransactionsStatus: vi.fn(),
};

const mockTransactionSync = {
  syncTransactionsByChains: vi.fn().mockResolvedValue(undefined),
};

const mockAccountCategorization = {
  categorizeAccountsByType: vi.fn((accounts: ChainAddress[]) => ({
    bitcoinAccounts: accounts.filter(a => a.chain === 'btc'),
    evmAccounts: accounts.filter(a => ['eth', 'optimism', 'polygon_pos'].includes(a.chain)),
    evmLikeAccounts: [],
    solanaAccounts: [],
  })),
};

const mockRefreshHandlers = {
  queryAllExchangeEvents: vi.fn().mockResolvedValue(undefined),
  queryOnlineEvent: vi.fn().mockResolvedValue(undefined),
};

const mockSessionSettingsStore = {
  connectedExchanges: ref<Exchange[]>(mockExchanges),
};

vi.mock('./use-history-transaction-accounts', () => ({
  useHistoryTransactionAccounts: vi.fn(() => mockHistoryTransactionAccounts),
}));

vi.mock('@/composables/status', () => ({
  useStatusUpdater: vi.fn(() => mockStatusUpdater),
}));

vi.mock('./decoding', () => ({
  useHistoryTransactionDecoding: vi.fn(() => mockHistoryTransactionDecoding),
}));

vi.mock('@/store/history', () => ({
  useHistoryStore: vi.fn(() => mockHistoryStore),
}));

vi.mock('./use-transaction-sync', () => ({
  useTransactionSync: vi.fn(() => mockTransactionSync),
}));

vi.mock('./use-account-categorization', () => ({
  useAccountCategorization: vi.fn(() => mockAccountCategorization),
}));

vi.mock('./refresh-handlers', () => ({
  useRefreshHandlers: vi.fn(() => mockRefreshHandlers),
}));

vi.mock('@/store/settings/session', () => ({
  useSessionSettingsStore: vi.fn(() => mockSessionSettingsStore),
}));

vi.mock('@/store/history/query-status/tx-query-status', () => ({
  useTxQueryStatusStore: vi.fn(() => mockTxQueryStatusStore),
}));

vi.mock('@/store/history/query-status/events-query-status', () => ({
  useEventsQueryStatusStore: vi.fn(() => mockEventsQueryStatusStore),
}));

describe('useRefreshTransactions', () => {
  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);

    // Reset the refresh state store
    const refreshStateStore = useHistoryRefreshStateStore();
    refreshStateStore.reset();

    vi.clearAllMocks();
    mockStatusUpdater.fetchDisabled.mockReturnValue(false);
    mockStatusUpdater.isFirstLoad.mockReturnValue(true);

    // Reset mock return values to defaults
    mockHistoryTransactionAccounts.getBitcoinAccounts.mockReturnValue(mockBitcoinAccounts);
    mockHistoryTransactionAccounts.getEvmAccounts.mockReturnValue(mockEvmAccounts);
    mockHistoryTransactionAccounts.getEvmLikeAccounts.mockReturnValue([]);
    mockHistoryTransactionAccounts.getSolanaAccounts.mockReturnValue([]);
  });

  describe('basic refresh flow', () => {
    it('should perform full refresh when called without parameters', async () => {
      const { refreshTransactions } = useRefreshTransactions();

      await refreshTransactions();

      expect(mockStatusUpdater.setStatus).toHaveBeenCalledWith(Status.LOADING);
      expect(mockTxQueryStatusStore.initializeQueryStatus).toHaveBeenCalled();
      expect(mockHistoryStore.resetUndecodedTransactionsStatus).toHaveBeenCalled();
      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalled();
      expect(mockRefreshHandlers.queryAllExchangeEvents).toHaveBeenCalled();
      expect(mockStatusUpdater.setStatus).toHaveBeenCalledWith(Status.LOADED);
    });

    it('should skip refresh when fetchDisabled returns true and no new accounts', async () => {
      mockStatusUpdater.fetchDisabled.mockReturnValue(true);

      // First, perform a refresh to mark all accounts/exchanges as refreshed
      const { refreshTransactions } = useRefreshTransactions();
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
      const { refreshTransactions } = useRefreshTransactions();

      await refreshTransactions();

      expect(mockStatusUpdater.setStatus).toHaveBeenCalledWith(Status.LOADING);
    });

    it('should set REFRESHING status on subsequent loads', async () => {
      mockStatusUpdater.isFirstLoad.mockReturnValue(false);
      const { refreshTransactions } = useRefreshTransactions();

      await refreshTransactions();

      expect(mockStatusUpdater.setStatus).toHaveBeenCalledWith(Status.REFRESHING);
    });
  });

  describe('account-specific refresh', () => {
    it('should refresh only specified accounts', async () => {
      const { refreshTransactions } = useRefreshTransactions();
      const specificAccounts = [mockEvmAccounts[0]];

      await refreshTransactions({
        payload: { accounts: specificAccounts },
        userInitiated: true, // Ensure it bypasses any "already refreshed" logic
      });

      expect(mockAccountCategorization.categorizeAccountsByType).toHaveBeenCalledWith(
        specificAccounts,
      );
      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalled();
    });

    it('should not query exchanges when only accounts are specified', async () => {
      const { refreshTransactions } = useRefreshTransactions();

      await refreshTransactions({
        payload: { accounts: mockEvmAccounts },
      });

      expect(mockRefreshHandlers.queryAllExchangeEvents).not.toHaveBeenCalled();
      expect(mockEventsQueryStatusStore.resetQueryStatus).toHaveBeenCalled();
    });
  });

  describe('exchange refresh', () => {
    it('should refresh exchanges when exchanges are specified', async () => {
      const { refreshTransactions } = useRefreshTransactions();

      await refreshTransactions({
        payload: { exchanges: mockExchanges },
      });

      expect(mockEventsQueryStatusStore.initializeQueryStatus).toHaveBeenCalledWith(mockExchanges);
      expect(mockRefreshHandlers.queryAllExchangeEvents).toHaveBeenCalledWith(mockExchanges);
    });

    it('should refresh all connected exchanges in full refresh', async () => {
      const { refreshTransactions } = useRefreshTransactions();

      await refreshTransactions();

      expect(mockRefreshHandlers.queryAllExchangeEvents).toHaveBeenCalledWith(undefined);
      expect(mockEventsQueryStatusStore.initializeQueryStatus).toHaveBeenCalled();
    });
  });

  describe('new account detection', () => {
    it('should bypass fetchDisabled when new accounts are detected', async () => {
      mockStatusUpdater.fetchDisabled.mockReturnValue(true);
      const { refreshTransactions } = useRefreshTransactions();

      await refreshTransactions();

      // Even with fetchDisabled true, should proceed due to new accounts
      expect(mockStatusUpdater.setStatus).toHaveBeenCalledWith(Status.LOADING);
    });
  });

  describe('new exchange detection', () => {
    it('should bypass fetchDisabled when new exchanges are detected', async () => {
      mockStatusUpdater.fetchDisabled.mockReturnValue(true);
      const { refreshTransactions } = useRefreshTransactions();

      await refreshTransactions();

      // Even with fetchDisabled true, should proceed due to new exchanges
      expect(mockStatusUpdater.setStatus).toHaveBeenCalledWith(Status.LOADING);
    });
  });

  describe('concurrent refresh handling', () => {
    it('should add new accounts to pending when refresh is running', async () => {
      vi.useFakeTimers();

      const { refreshTransactions } = useRefreshTransactions();
      const firstRefresh = refreshTransactions();

      // Trigger another refresh while first is running
      await refreshTransactions({
        payload: { accounts: [mockEvmAccounts[0]] },
      });

      await firstRefresh;

      await vi.advanceTimersByTimeAsync(150);

      // Should be called 3 times: first refresh (EVM + Bitcoin) + pending refresh (EVM)
      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalledTimes(3);

      vi.useRealTimers();
    });
  });

  describe('chain filtering', () => {
    it('should filter accounts by specified chains', async () => {
      const { refreshTransactions } = useRefreshTransactions();

      await refreshTransactions({
        chains: ['eth'],
      });

      expect(mockHistoryTransactionAccounts.getEvmAccounts).toHaveBeenCalledWith(['eth']);
      expect(mockHistoryTransactionAccounts.getBitcoinAccounts).toHaveBeenCalledWith(['eth']);
      expect(mockHistoryTransactionAccounts.getSolanaAccounts).toHaveBeenCalledWith(['eth']);
    });
  });

  describe('disableEvmEvents parameter', () => {
    it('should skip undecoded transactions when disableEvmEvents is true', async () => {
      const { refreshTransactions } = useRefreshTransactions();

      await refreshTransactions({
        disableEvmEvents: true,
      });

      expect(mockHistoryTransactionDecoding.fetchUndecodedTransactionsStatus).not.toHaveBeenCalled();
    });

    it('should fetch undecoded transactions when disableEvmEvents is false', async () => {
      const { refreshTransactions } = useRefreshTransactions();

      await refreshTransactions({
        disableEvmEvents: false,
      });

      expect(mockHistoryTransactionDecoding.fetchUndecodedTransactionsStatus).toHaveBeenCalled();
    });
  });

  describe('online queries', () => {
    it('should execute ETH_WITHDRAWALS and BLOCK_PRODUCTIONS queries on full refresh', async () => {
      const { refreshTransactions } = useRefreshTransactions();

      await refreshTransactions();

      expect(mockRefreshHandlers.queryOnlineEvent).toHaveBeenCalledWith(
        OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
      );
      expect(mockRefreshHandlers.queryOnlineEvent).toHaveBeenCalledWith(
        OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS,
      );
    });

    it('should execute custom queries when specified', async () => {
      const { refreshTransactions } = useRefreshTransactions();

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
      const { refreshTransactions } = useRefreshTransactions();

      await refreshTransactions();

      expect(mockStatusUpdater.setStatus).toHaveBeenCalledWith(Status.LOADED);
    });

    it('should continue with other operations when one fails', async () => {
      mockTransactionSync.syncTransactionsByChains.mockRejectedValue(new Error('Sync failed'));
      const { refreshTransactions } = useRefreshTransactions();

      await refreshTransactions();

      expect(mockHistoryTransactionDecoding.fetchUndecodedTransactionsBreakdown).toHaveBeenCalled();
    });
  });

  describe('transaction chain type sync', () => {
    it('should sync EVM transactions', async () => {
      const { refreshTransactions } = useRefreshTransactions();

      await refreshTransactions();

      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalledWith(
        expect.objectContaining({
          accounts: mockEvmAccounts,
          type: expect.any(String),
        }),
      );
    });

    it('should sync Bitcoin transactions', async () => {
      const { refreshTransactions } = useRefreshTransactions();

      await refreshTransactions();

      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalledWith(
        expect.objectContaining({
          accounts: mockBitcoinAccounts,
          type: expect.any(String),
        }),
      );
    });

    it('should not sync transactions for empty account types', async () => {
      mockHistoryTransactionAccounts.getBitcoinAccounts.mockReturnValue([]);
      mockHistoryTransactionAccounts.getEvmAccounts.mockReturnValue([]);
      mockHistoryTransactionAccounts.getSolanaAccounts.mockReturnValue([]);
      mockHistoryTransactionAccounts.getEvmLikeAccounts.mockReturnValue([]);

      const { refreshTransactions } = useRefreshTransactions();

      await refreshTransactions();

      expect(mockTransactionSync.syncTransactionsByChains).not.toHaveBeenCalled();
    });
  });

  describe('query status management', () => {
    it('should initialize query status for EVM accounts', async () => {
      const { refreshTransactions } = useRefreshTransactions();

      await refreshTransactions();

      expect(mockTxQueryStatusStore.initializeQueryStatus).toHaveBeenCalledWith(mockEvmAccounts);
    });

    it('should reset query status when no accounts to refresh', async () => {
      mockHistoryTransactionAccounts.getBitcoinAccounts.mockReturnValue([]);
      mockHistoryTransactionAccounts.getEvmAccounts.mockReturnValue([]);
      mockHistoryTransactionAccounts.getSolanaAccounts.mockReturnValue([]);
      mockHistoryTransactionAccounts.getEvmLikeAccounts.mockReturnValue([]);

      const { refreshTransactions } = useRefreshTransactions();

      await refreshTransactions({
        payload: { accounts: [], exchanges: [] },
      });

      expect(mockTxQueryStatusStore.resetQueryStatus).toHaveBeenCalled();
    });
  });

  describe('userInitiated parameter', () => {
    it('should pass userInitiated to fetchDisabled check', async () => {
      const { refreshTransactions } = useRefreshTransactions();

      await refreshTransactions({ userInitiated: true });

      expect(mockStatusUpdater.fetchDisabled).toHaveBeenCalledWith(true);
    });

    it('should default userInitiated to false', async () => {
      const { refreshTransactions } = useRefreshTransactions();

      await refreshTransactions();

      expect(mockStatusUpdater.fetchDisabled).toHaveBeenCalledWith(false);
    });
  });
});
