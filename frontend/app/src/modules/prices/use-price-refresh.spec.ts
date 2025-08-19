import { bigNumberify, Blockchain } from '@rotki/common';
import { createTestBalance, createTestManualBalance, createTestPriceInfo } from '@test/utils/create-data';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TRADE_LOCATION_BANKS } from '@/data/defaults';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useCurrencies } from '@/types/currencies';
import '@test/i18n';

// Mock functions
const mockCacheEuroCollectionAssets = vi.fn();
const mockFetchExchangeRates = vi.fn();
const mockFetchPrices = vi.fn();

// Mock the price task manager at the top level
vi.mock('@/modules/prices/use-price-task-manager', (): any => ({
  usePriceTaskManager: () => ({
    cacheEuroCollectionAssets: mockCacheEuroCollectionAssets,
    fetchExchangeRates: mockFetchExchangeRates,
    fetchPrices: mockFetchPrices,
  }),
}));

// Import after mocking
const { usePriceRefresh } = await import('@/modules/prices/use-price-refresh');

describe('usePriceRefresh', () => {
  beforeEach(() => {
    setActivePinia(createPinia());

    // Reset mocks before each test
    mockCacheEuroCollectionAssets.mockClear().mockResolvedValue({});
    mockFetchExchangeRates.mockClear().mockResolvedValue({});
    mockFetchPrices.mockClear().mockResolvedValue({});
  });

  describe('adjustPrices', () => {
    it('should handle currency conversion without breaking calculations', () => {
      const { exchangeBalances } = storeToRefs(useBalancesStore());
      const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
      const { adjustPrices } = usePriceRefresh();

      set(connectedExchanges, [{
        location: 'kraken',
        name: 'Bitrex Acc',
      }]);

      set(exchangeBalances, {
        kraken: {
          BTC: createTestBalance(50, 50),
          DAI: createTestBalance(50, 50),
          ETH: createTestBalance(50, 50),
          EUR: createTestBalance(50, 50),
        },
      });

      const { prices } = storeToRefs(useBalancePricesStore());

      const { exchangeRates } = storeToRefs(useBalancePricesStore());
      set(exchangeRates, { EUR: bigNumberify(1.2) });

      const { currencies } = useCurrencies();
      updateGeneralSettings({
        mainCurrency: get(currencies)[1],
      });

      set(prices, {
        BTC: createTestPriceInfo(40000),
        DAI: createTestPriceInfo(1),
        ETH: createTestPriceInfo(3000),
        EUR: createTestPriceInfo(1),
        SAI: createTestPriceInfo(1),
      });

      const { manualBalances } = storeToRefs(useBalancesStore());

      set(manualBalances, [
        createTestManualBalance('DAI', 50, 50, TRADE_LOCATION_BANKS),
      ]);

      const { balances: allBalances } = storeToRefs(useBalancesStore());

      set(allBalances, {
        [Blockchain.ETH]: {
          '0x123': {
            assets: {
              BTC: { address: createTestBalance(100, 100) },
              DAI: { address: createTestBalance(100, 100) },
              ETH: { address: createTestBalance(100, 100) },
              SAI: { address: createTestBalance(100, 100) },
            },
            liabilities: {},
          },
        },
      });

      // Test adjustPrices function
      adjustPrices(get(prices));

      // Verify that prices were adjusted correctly
      const { prices: adjustedPrices } = storeToRefs(useBalancePricesStore());
      const pricesAfterAdjustment = get(adjustedPrices);

      expect(pricesAfterAdjustment.BTC?.value).toEqual(bigNumberify(40000));
      expect(pricesAfterAdjustment.DAI?.value).toEqual(bigNumberify(1));
      expect(pricesAfterAdjustment.ETH?.value).toEqual(bigNumberify(3000));
      expect(pricesAfterAdjustment.EUR?.value).toEqual(bigNumberify(1));
      expect(pricesAfterAdjustment.SAI?.value).toEqual(bigNumberify(1));
    });

    it('should update balances correctly when called with new prices', () => {
      const { adjustPrices } = usePriceRefresh();
      const { exchangeBalances } = storeToRefs(useBalancesStore());

      // Set up initial exchange balances
      set(exchangeBalances, {
        kraken: {
          BTC: createTestBalance(1, 40000),
          ETH: createTestBalance(2, 6000),
        },
      });

      const newPrices = {
        BTC: createTestPriceInfo(50000),
        ETH: createTestPriceInfo(4000),
      };

      adjustPrices(newPrices);

      // The adjustPrices function should update the balance calculations
      // Verify that the function completes without error
      const updatedBalances = get(exchangeBalances);
      expect(updatedBalances.kraken.BTC.amount).toEqual(bigNumberify(1));
      expect(updatedBalances.kraken.ETH.amount).toEqual(bigNumberify(2));
    });

    it('should handle empty prices object', () => {
      const { adjustPrices } = usePriceRefresh();
      const { prices } = storeToRefs(useBalancePricesStore());

      // Set initial prices
      set(prices, {
        BTC: createTestPriceInfo(40000),
      });

      // Adjust with empty object
      adjustPrices({});

      const updatedPrices = get(prices);
      // Should still have the previous prices since adjustPrices spreads the new prices
      expect(updatedPrices.BTC?.value).toEqual(bigNumberify(40000));
    });
  });

  describe('refreshPrice', () => {
    it('should handle single asset price refresh', async () => {
      const { refreshPrice } = usePriceRefresh();

      // This test mainly verifies the function doesn't throw errors
      // In a real test environment, you'd mock the actual price fetching
      await expect(refreshPrice('BTC')).resolves.not.toThrow();
    });
  });

  describe('refreshPrices', () => {
    it('should handle bulk price refresh', async () => {
      const { refreshPrices } = usePriceRefresh();

      // This test mainly verifies the function doesn't throw errors
      await expect(refreshPrices()).resolves.not.toThrow();
    });

    it('should handle selected assets parameter', async () => {
      const { refreshPrices } = usePriceRefresh();

      // Test with specific assets
      await expect(refreshPrices(false, ['BTC', 'ETH'])).resolves.not.toThrow();
    });

    it('should handle ignoreCache parameter', async () => {
      const { refreshPrices } = usePriceRefresh();

      // Test with ignoreCache = true
      await expect(refreshPrices(true)).resolves.not.toThrow();
    });
  });

  describe('queue fifo', () => {
    let executionOrder: string[];
    let callCount: number;
    let processingCount: number;
    let maxConcurrent: number;

    beforeEach(() => {
      // Reset execution tracking variables
      executionOrder = [];
      callCount = 0;
      processingCount = 0;
      maxConcurrent = 0;
    });

    it('should process price refresh requests sequentially in FIFO order', async () => {
      const { refreshPrice, refreshPrices } = usePriceRefresh();

      // Configure mock for execution order tracking
      mockFetchPrices.mockImplementation(async (params: any) =>
        // Add a small delay to simulate async operation
        new Promise((resolve) => {
          setTimeout(() => {
            executionOrder.push(params.selectedAssets.join(','));
            resolve({});
          }, 10);
        }),
      );

      // Fire multiple requests simultaneously
      const promise1 = refreshPrice('BTC');
      const promise2 = refreshPrices(false, ['ETH', 'DAI']);
      const promise3 = refreshPrice('USDT');

      // Wait for all to complete
      await Promise.all([promise1, promise2, promise3]);

      // Verify they executed in FIFO order
      expect(executionOrder).toEqual(['BTC', 'ETH,DAI', 'USDT']);
    });

    it('should handle errors in queue without breaking subsequent tasks', async () => {
      const { refreshPrice } = usePriceRefresh();

      // Configure mock to fail on second call
      mockFetchPrices.mockImplementation(async () => {
        callCount++;
        if (callCount === 2) {
          return Promise.reject(new Error('Network error'));
        }
        return Promise.resolve({});
      });

      // First request should succeed
      await expect(refreshPrice('BTC')).resolves.not.toThrow();

      // Second request should fail
      await expect(refreshPrice('ETH')).rejects.toThrow('Network error');

      // Third request should still succeed
      await expect(refreshPrice('DAI')).resolves.not.toThrow();
    });

    it('should not start multiple queue processors simultaneously', async () => {
      const { refreshPrices } = usePriceRefresh();

      // Configure mock to track concurrent executions
      mockFetchPrices.mockImplementation(async () => {
        processingCount++;
        maxConcurrent = Math.max(maxConcurrent, processingCount);

        return new Promise((resolve) => {
          setTimeout(() => {
            processingCount--;
            resolve({});
          }, 20);
        });
      });

      // Fire multiple requests simultaneously
      const promises = [
        refreshPrices(false, ['BTC']),
        refreshPrices(false, ['ETH']),
        refreshPrices(false, ['DAI']),
        refreshPrices(false, ['USDT']),
      ];

      await Promise.all(promises);

      // Should never have more than 1 concurrent execution
      expect(maxConcurrent).toBe(1);
    });
  });
});
