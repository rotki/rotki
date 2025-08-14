import type { usePriceUtils } from '@/modules/prices/use-price-utils';
import { type AssetBalanceWithPriceAndChains, BigNumber } from '@rotki/common';
import { get } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, type ComputedRef, ref } from 'vue';
import { defaultGeneralSettings } from '@/data/factories';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useCurrencies } from '@/types/currencies';
import { useStatisticsStore } from './index';

function createBalanceWithPrice(
  amount: string,
  asset: string,
  usdPrice: string,
): AssetBalanceWithPriceAndChains {
  const amountBN = new BigNumber(amount);
  const priceBN = new BigNumber(usdPrice);
  const usdValue = amountBN.multipliedBy(priceBN);

  return {
    amount: amountBN,
    asset,
    usdPrice: priceBN,
    usdValue,
  };
}

vi.mock('@/composables/balances/use-aggregated-balances', () => ({
  useAggregatedBalances: vi.fn(() => ({
    balances: (): ComputedRef<AssetBalanceWithPriceAndChains[]> => computed<AssetBalanceWithPriceAndChains[]>(() => [
      createBalanceWithPrice('10000', 'JPY', '0.01'),
      createBalanceWithPrice('2', 'ETH', '2000'),
      createBalanceWithPrice('0.5', 'BTC', '40000'),
    ]),
    liabilities: (): ComputedRef<AssetBalanceWithPriceAndChains[]> => computed<AssetBalanceWithPriceAndChains[]>(() => [
      createBalanceWithPrice('1000', 'USD', '1'),
    ]),
  })),
}));

vi.mock('@/composables/utils/useNumberScrambler', () => ({
  useNumberScrambler: vi.fn(({ value }) => value),
}));

vi.mock('@/modules/prices/use-price-utils', () => ({
  usePriceUtils: (): Pick<ReturnType<typeof usePriceUtils>, 'useExchangeRate'> => ({
    useExchangeRate: (currency: any): any => computed(() => {
      if (get(currency) === 'JPY')
        return new BigNumber('150'); // 1 USD = 150 JPY
      if (get(currency) === 'EUR')
        return new BigNumber('0.9'); // 1 USD = 0.9 EUR
      return new BigNumber('1');
    }),
  }),
}));

describe('useStatisticsStore', () => {
  let generalSettings: ReturnType<typeof useGeneralSettingsStore>;
  let currencies: ReturnType<typeof useCurrencies>;

  beforeEach(() => {
    setActivePinia(createPinia());

    // Initialize stores
    generalSettings = useGeneralSettingsStore();
    currencies = useCurrencies();

    // Reset currency to USD before each test
    generalSettings.update({
      ...defaultGeneralSettings(currencies.findCurrency('USD')),
      mainCurrency: currencies.findCurrency('USD'),
    });
  });

  describe('calculateTotalValue with main currency handling', () => {
    it('should use amount directly for main currency assets and convert USD values for others', () => {
      // Set the currency to JPY before creating the store
      generalSettings.update({
        ...defaultGeneralSettings(currencies.findCurrency('JPY')),
        mainCurrency: currencies.findCurrency('JPY'),
      });

      const store = useStatisticsStore();
      const totalValue = get(store.totalNetWorth);

      // Expected calculation:
      // JPY asset: 10000 JPY (used directly as it's the main currency)
      // ETH asset: 4000 USD * 150 = 600000 JPY
      // BTC asset: 20000 USD * 150 = 3000000 JPY
      // Total assets: 10000 + 600000 + 3000000 = 3610000 JPY
      // Liabilities (USD): 1000 USD * 150 = 150000 JPY
      // Net worth: 3610000 - 150000 = 3460000 JPY

      expect(totalValue.toNumber()).toBe(3460000);
    });

    it('should correctly calculate when USD is the main currency', () => {
      // USD is already the default
      const store = useStatisticsStore();
      const totalValue = get(store.totalNetWorth);

      // Expected calculation:
      // JPY asset: 100 USD (using usdValue)
      // ETH asset: 4000 USD
      // BTC asset: 20000 USD
      // Total assets: 100 + 4000 + 20000 = 24100 USD
      // Liabilities (USD): 1000 USD (used directly as it's the main currency)
      // Net worth: 24100 - 1000 = 23100 USD

      expect(totalValue.toNumber()).toBe(23100);
    });

    it('should correctly handle EUR as main currency', () => {
      // Set the currency to EUR before creating the store
      generalSettings.update({
        ...defaultGeneralSettings(currencies.findCurrency('EUR')),
        mainCurrency: currencies.findCurrency('EUR'),
      });

      const store = useStatisticsStore();
      const totalValue = get(store.totalNetWorth);

      // Expected calculation:
      // JPY asset: 100 USD * 0.9 = 90 EUR
      // ETH asset: 4000 USD * 0.9 = 3600 EUR
      // BTC asset: 20000 USD * 0.9 = 18000 EUR
      // Total assets: 90 + 3600 + 18000 = 21690 EUR
      // Liabilities (USD): 1000 USD * 0.9 = 900 EUR
      // Net worth: 21690 - 900 = 20790 EUR

      expect(totalValue.toNumber()).toBe(20790);
    });

    it('should correctly handle when main currency appears in liabilities', async () => {
      // Update the mock for this specific test
      const module = await import('@/composables/balances/use-aggregated-balances');
      vi.mocked(module.useAggregatedBalances).mockImplementationOnce(() => ({
        assetPriceInfo: vi.fn() as any,
        assets: ref<string[]>([]) as any,
        balances: (): ComputedRef<AssetBalanceWithPriceAndChains[]> => computed<AssetBalanceWithPriceAndChains[]>(() => [
          createBalanceWithPrice('2', 'ETH', '2000'),
        ]),
        balancesByLocation: ref<Record<string, BigNumber>>({}) as any,
        liabilities: (): ComputedRef<AssetBalanceWithPriceAndChains[]> => computed<AssetBalanceWithPriceAndChains[]>(() => [
          createBalanceWithPrice('5000', 'JPY', '0.01'),
          createBalanceWithPrice('1000', 'USD', '1'),
        ]),
        useBlockchainBalances: vi.fn() as any,
        useExchangeBalances: vi.fn() as any,
        useLocationBreakdown: vi.fn() as any,
      }));

      // Set the currency to JPY before creating the store
      generalSettings.update({
        ...defaultGeneralSettings(currencies.findCurrency('JPY')),
        mainCurrency: currencies.findCurrency('JPY'),
      });

      const store = useStatisticsStore();
      const totalValue = get(store.totalNetWorth);

      // Expected calculation:
      // ETH asset: 4000 USD * 150 = 600000 JPY
      // Total assets: 600000 JPY
      // JPY liability: 5000 JPY (used directly as it's the main currency)
      // USD liability: 1000 USD * 150 = 150000 JPY
      // Total liabilities: 5000 + 150000 = 155000 JPY
      // Net worth: 600000 - 155000 = 445000 JPY

      expect(totalValue.toNumber()).toBe(445000);
    });
  });

  describe('totalNetWorth', () => {
    it('should not double-apply exchange rate', () => {
      // Set the currency to JPY before creating the store
      generalSettings.update({
        ...defaultGeneralSettings(currencies.findCurrency('JPY')),
        mainCurrency: currencies.findCurrency('JPY'),
      });

      const store = useStatisticsStore();
      const totalValue = get(store.totalNetWorth);

      // Verify totalNetWorth equals calculateTotalValue without additional multiplication
      expect(totalValue.toNumber()).toBe(3460000);
    });
  });
});
