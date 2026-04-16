import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBalanceFetching } from './use-balance-fetching';
import '@test/i18n';

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

  describe('autoRefresh', () => {
    it('should perform auto refresh of balances and prices', async () => {
      const { autoRefresh } = useBalanceFetching();
      await expect(autoRefresh()).resolves.not.toThrow();
    });
  });
});
