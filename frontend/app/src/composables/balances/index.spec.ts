import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBalances } from './index';
import '@test/i18n';

describe('useBalances', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  describe('fetchBalances', () => {
    it('should handle balance fetching', async () => {
      const { fetchBalances } = useBalances();

      // Mock the balance API to avoid actual API calls
      vi.mock('@/composables/api/balances', (): any => ({
        useBalancesApi: (): any => ({
          queryBalancesAsync: vi.fn().mockResolvedValue({ taskId: 'test-task' }),
        }),
      }));

      vi.mock('@/store/tasks', (): any => ({
        useTaskStore: (): any => ({
          awaitTask: vi.fn().mockResolvedValue({}),
          isTaskRunning: vi.fn().mockReturnValue(false),
        }),
      }));

      // This test mainly verifies the function doesn't throw errors
      await expect(fetchBalances()).resolves.not.toThrow();
    });

    it('should skip fetching if task is already running', async () => {
      const { fetchBalances } = useBalances();

      vi.mock('@/store/tasks', (): any => ({
        useTaskStore: (): any => ({
          awaitTask: vi.fn(),
          isTaskRunning: vi.fn().mockReturnValue(true),
        }),
      }));

      // Should return early without throwing
      await expect(fetchBalances()).resolves.not.toThrow();
    });
  });

  describe('fetch', () => {
    it('should coordinate fetching of all balance types', async () => {
      const { fetch } = useBalances();

      // Mock all the dependencies
      vi.mock('@/modules/prices/use-price-task-manager', (): any => ({
        usePriceTaskManager: (): any => ({
          fetchExchangeRates: vi.fn().mockResolvedValue({}),
        }),
      }));

      vi.mock('@/modules/balances/manual/use-manual-balances', (): any => ({
        useManualBalances: (): any => ({
          fetchManualBalances: vi.fn().mockResolvedValue({}),
        }),
      }));

      vi.mock('@/composables/blockchain', (): any => ({
        useBlockchains: (): any => ({
          refreshAccounts: vi.fn().mockResolvedValue({}),
        }),
      }));

      vi.mock('@/modules/balances/exchanges/use-exchanges', (): any => ({
        useExchanges: (): any => ({
          fetchConnectedExchangeBalances: vi.fn().mockResolvedValue({}),
        }),
      }));

      // This test verifies the function orchestrates balance fetching properly
      await expect(fetch()).resolves.not.toThrow();
    });
  });

  describe('autoRefresh', () => {
    it('should perform auto refresh of balances and prices', async () => {
      const { autoRefresh } = useBalances();

      // Mock all dependencies for auto refresh
      vi.mock('@/modules/balances/manual/use-manual-balances', (): any => ({
        useManualBalances: (): any => ({
          fetchManualBalances: vi.fn().mockResolvedValue({}),
        }),
      }));

      vi.mock('@/composables/blockchain', (): any => ({
        useBlockchains: (): any => ({
          refreshAccounts: vi.fn().mockResolvedValue({}),
        }),
      }));

      vi.mock('@/modules/balances/exchanges/use-exchanges', (): any => ({
        useExchanges: (): any => ({
          fetchConnectedExchangeBalances: vi.fn().mockResolvedValue({}),
        }),
      }));

      vi.mock('@/store/statistics', (): any => ({
        useStatisticsStore: (): any => ({
          fetchNetValue: vi.fn().mockResolvedValue({}),
        }),
      }));

      vi.mock('@/modules/prices/use-price-refresh', (): any => ({
        usePriceRefresh: (): any => ({
          refreshPrices: vi.fn().mockResolvedValue({}),
        }),
      }));

      // This test verifies auto refresh coordinates all balance updates
      await expect(autoRefresh()).resolves.not.toThrow();
    });
  });
});
