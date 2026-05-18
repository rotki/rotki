import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBalanceFetching } from './use-balance-fetching';
import '@test/i18n';

const { refreshBlockchainBalances, maybeDetect, skipReason, willDetect } = vi.hoisted(() => ({
  maybeDetect: vi.fn().mockResolvedValue(undefined),
  refreshBlockchainBalances: vi.fn().mockResolvedValue(undefined),
  skipReason: vi.fn().mockReturnValue('auto-detect-tokens disabled'),
  willDetect: vi.fn().mockReturnValue(false),
}));

vi.mock('@/modules/balances/use-blockchain-balances', () => ({
  useBlockchainBalances: vi.fn().mockReturnValue({
    fetchBlockchainBalances: vi.fn().mockResolvedValue({}),
    refreshBlockchainBalances,
  }),
}));

vi.mock('@/modules/balances/blockchain/use-auto-token-detection', () => ({
  useAutoTokenDetection: (): { maybeDetect: typeof maybeDetect; skipReason: typeof skipReason; willDetect: typeof willDetect } => ({
    maybeDetect,
    skipReason,
    willDetect,
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const { computed } = await import('vue');
  const { Blockchain } = await import('@rotki/common');
  return {
    useSupportedChains: vi.fn().mockReturnValue({
      supportedChains: computed(() => [
        { id: Blockchain.ETH, type: 'evm', name: 'Ethereum', image: '', nativeToken: 'ETH' },
        { id: Blockchain.BTC, type: 'bitcoin', name: 'Bitcoin', image: '', nativeToken: 'BTC' },
      ]),
      txEvmChains: computed(() => [
        { id: Blockchain.ETH, evmChainName: 'ethereum', type: 'evm', name: 'Ethereum', image: '', nativeToken: 'ETH' },
      ]),
    }),
  };
});

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn().mockReturnValue({
    notifyError: vi.fn(),
  }),
  getErrorMessage: vi.fn(),
}));

vi.mock('@/modules/core/tasks/use-task-handler', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useTaskHandler: vi.fn().mockReturnValue({
    runTask: vi.fn().mockImplementation(async (taskFn: () => Promise<unknown>): Promise<unknown> => {
      await taskFn();
      return { success: true, result: {} };
    }),
  }),
}));

vi.mock('@/modules/balances/api/use-balances-api', () => ({
  useBalancesApi: vi.fn().mockReturnValue({
    queryBalancesAsync: vi.fn().mockResolvedValue({ taskId: 1 }),
  }),
}));

vi.mock('@/modules/assets/prices/use-price-task-manager', () => ({
  usePriceTaskManager: vi.fn().mockReturnValue({
    fetchExchangeRates: vi.fn().mockResolvedValue({}),
  }),
}));

vi.mock('@/modules/balances/manual/use-manual-balances', () => ({
  useManualBalances: vi.fn().mockReturnValue({
    fetchManualBalances: vi.fn().mockResolvedValue({}),
  }),
}));

vi.mock('@/modules/accounts/use-blockchain-account-management', () => ({
  useBlockchainAccountManagement: vi.fn().mockReturnValue({
    refreshAccounts: vi.fn().mockResolvedValue({}),
  }),
}));

vi.mock('@/modules/balances/exchanges/use-exchanges', () => ({
  useExchanges: vi.fn().mockReturnValue({
    fetchConnectedExchangeBalances: vi.fn().mockResolvedValue({}),
  }),
}));

vi.mock('@/modules/statistics/use-statistics-data-fetching', () => ({
  useStatisticsDataFetching: vi.fn().mockReturnValue({
    fetchNetValue: vi.fn().mockResolvedValue({}),
  }),
}));

vi.mock('@/modules/assets/prices/use-price-refresh', () => ({
  usePriceRefresh: vi.fn().mockReturnValue({
    refreshPrices: vi.fn().mockResolvedValue({}),
  }),
}));

describe('useBalanceFetching', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  describe('fetchBalances', () => {
    it('should handle balance fetching', async () => {
      const { fetchBalances } = useBalanceFetching();
      await expect(fetchBalances()).resolves.not.toThrow();
    });
  });

  describe('fetch', () => {
    it('should coordinate fetching of all balance types', async () => {
      const { fetch } = useBalanceFetching();
      await expect(fetch()).resolves.not.toThrow();
    });
  });

  describe('refreshFromChain', () => {
    beforeEach(() => {
      refreshBlockchainBalances.mockClear();
      maybeDetect.mockClear();
      willDetect.mockReset();
    });

    it('should refresh all chains from network when detection is not going to run', async () => {
      willDetect.mockReturnValue(false);
      const { refreshFromChain } = useBalanceFetching();

      refreshFromChain();
      await flushPromises();

      expect(refreshBlockchainBalances).toHaveBeenCalledTimes(1);
      expect(refreshBlockchainBalances).toHaveBeenCalledWith();
      expect(maybeDetect).not.toHaveBeenCalled();
    });

    it('should run detection and refresh only non-EVM chains from network when detection will run', async () => {
      willDetect.mockReturnValue(true);
      const { refreshFromChain } = useBalanceFetching();

      refreshFromChain();
      await flushPromises();

      expect(maybeDetect).toHaveBeenCalledTimes(1);
      expect(refreshBlockchainBalances).toHaveBeenCalledTimes(1);
      expect(refreshBlockchainBalances).toHaveBeenCalledWith({ blockchain: ['btc'] });
    });
  });

  describe('autoRefresh', () => {
    it('should perform auto refresh of balances and prices', async () => {
      const { autoRefresh } = useBalanceFetching();
      await expect(autoRefresh()).resolves.not.toThrow();
    });
  });
});
