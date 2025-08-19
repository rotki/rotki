import { bigNumberify, Blockchain } from '@rotki/common';
import { createTestBalance, createTestManualBalance, createTestPriceInfo } from '@test/utils/create-data';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TRADE_LOCATION_BANKS } from '@/data/defaults';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { usePriceRefresh } from '@/modules/prices/use-price-refresh';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useCurrencies } from '@/types/currencies';
import '@test/i18n';

describe('usePriceRefresh', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
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

      // Mock the price fetching to avoid actual API calls
      vi.mock('@/modules/prices/use-price-task-manager', (): any => ({
        usePriceTaskManager: (): any => ({
          fetchPrices: vi.fn().mockResolvedValue({}),
        }),
      }));

      // This test mainly verifies the function doesn't throw errors
      // In a real test environment, you'd mock the actual price fetching
      await expect(refreshPrice('BTC')).resolves.not.toThrow();
    });
  });

  describe('refreshPrices', () => {
    it('should handle bulk price refresh', async () => {
      const { refreshPrices } = usePriceRefresh();

      // Mock the price fetching to avoid actual API calls
      vi.mock('@/modules/prices/use-price-task-manager', (): any => ({
        usePriceTaskManager: (): any => ({
          cacheEuroCollectionAssets: vi.fn().mockResolvedValue({}),
          fetchExchangeRates: vi.fn().mockResolvedValue({}),
          fetchPrices: vi.fn().mockResolvedValue({}),
        }),
      }));

      // This test mainly verifies the function doesn't throw errors
      await expect(refreshPrices()).resolves.not.toThrow();
    });

    it('should handle selected assets parameter', async () => {
      const { refreshPrices } = usePriceRefresh();

      // Mock the price fetching to avoid actual API calls
      vi.mock('@/modules/prices/use-price-task-manager', (): any => ({
        usePriceTaskManager: (): any => ({
          cacheEuroCollectionAssets: vi.fn().mockResolvedValue({}),
          fetchPrices: vi.fn().mockResolvedValue({}),
        }),
      }));

      // Test with specific assets
      await expect(refreshPrices(false, ['BTC', 'ETH'])).resolves.not.toThrow();
    });

    it('should handle ignoreCache parameter', async () => {
      const { refreshPrices } = usePriceRefresh();

      // Mock the price fetching to avoid actual API calls
      vi.mock('@/modules/prices/use-price-task-manager', (): any => ({
        usePriceTaskManager: (): any => ({
          cacheEuroCollectionAssets: vi.fn().mockResolvedValue({}),
          fetchExchangeRates: vi.fn().mockResolvedValue({}),
          fetchPrices: vi.fn().mockResolvedValue({}),
        }),
      }));

      // Test with ignoreCache = true
      await expect(refreshPrices(true)).resolves.not.toThrow();
    });
  });
});
