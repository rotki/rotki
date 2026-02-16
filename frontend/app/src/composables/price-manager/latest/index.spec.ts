import type { ManualPrice } from '@/types/prices';
import { bigNumberify } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useLatestPrices } from '@/composables/price-manager/latest';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useCurrencies } from '@/types/currencies';

vi.mock('@/composables/api/assets/prices', () => ({
  useAssetPricesApi: vi.fn().mockReturnValue({
    addLatestPrice: vi.fn().mockResolvedValue(true),
    deleteLatestPrice: vi.fn().mockResolvedValue(true),
    fetchLatestPrices: vi.fn().mockResolvedValue([]),
  }),
}));

vi.mock('@/modules/prices/use-price-refresh', () => ({
  usePriceRefresh: vi.fn().mockReturnValue({
    refreshPrices: vi.fn().mockResolvedValue(undefined),
  }),
}));

vi.mock('@/composables/status', () => ({
  useStatusUpdater: vi.fn().mockReturnValue({
    resetStatus: vi.fn(),
  }),
}));

function t(key: string): string {
  return key;
}

describe('useLatestPrices', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  function setupPrices(currency: string, exchangeRates: Record<string, number>, assetPrices: Record<string, number>): void {
    const { findCurrency } = useCurrencies();
    updateGeneralSettings({ mainCurrency: findCurrency(currency) });

    const store = useBalancePricesStore();
    const { exchangeRates: rates, prices } = storeToRefs(store);

    const priceEntries: Record<string, { isManualPrice: boolean; oracle: string; value: ReturnType<typeof bigNumberify> }> = {};
    for (const [asset, value] of Object.entries(assetPrices)) {
      priceEntries[asset] = {
        isManualPrice: false,
        oracle: 'coingecko',
        value: bigNumberify(value),
      };
    }
    set(prices, priceEntries);

    const rateEntries: Record<string, ReturnType<typeof bigNumberify>> = {};
    for (const [curr, rate] of Object.entries(exchangeRates)) {
      rateEntries[curr] = bigNumberify(rate);
    }
    set(rates, rateEntries);
  }

  describe('items', () => {
    it('computes usdPrice in current currency without double conversion', async () => {
      setupPrices('EUR', { EUR: 0.85 }, { ETH: 2000 });

      const { useAssetPricesApi } = await import('@/composables/api/assets/prices');
      const { fetchLatestPrices } = useAssetPricesApi();

      const manualPrices: ManualPrice[] = [
        { fromAsset: 'ETH', price: bigNumberify(123), toAsset: 'EUR' },
      ];
      vi.mocked(fetchLatestPrices).mockResolvedValue(manualPrices);

      const { items, getLatestPrices } = useLatestPrices(t as ReturnType<typeof useI18n>['t']);
      await getLatestPrices();

      const result = get(items);
      expect(result).toHaveLength(1);
      // ETH price is 2000 USD, with EUR rate 0.85, price in EUR = 2000 * 0.85 = 1700
      expect(result[0].usdPrice.toNumber()).toBe(1700);
    });

    it('computes usdPrice correctly when main currency is USD', async () => {
      setupPrices('USD', {}, { ETH: 2000 });

      const { useAssetPricesApi } = await import('@/composables/api/assets/prices');
      const { fetchLatestPrices } = useAssetPricesApi();

      const manualPrices: ManualPrice[] = [
        { fromAsset: 'ETH', price: bigNumberify(2000), toAsset: 'USD' },
      ];
      vi.mocked(fetchLatestPrices).mockResolvedValue(manualPrices);

      const { items, getLatestPrices } = useLatestPrices(t as ReturnType<typeof useI18n>['t']);
      await getLatestPrices();

      const result = get(items);
      expect(result).toHaveLength(1);
      // USD is the main currency, ETH price is 2000, no conversion needed
      expect(result[0].usdPrice.toNumber()).toBe(2000);
    });

    it('filters items when filter is provided', async () => {
      setupPrices('USD', {}, { ETH: 2000, BTC: 50000 });

      const { useAssetPricesApi } = await import('@/composables/api/assets/prices');
      const { fetchLatestPrices } = useAssetPricesApi();

      const manualPrices: ManualPrice[] = [
        { fromAsset: 'ETH', price: bigNumberify(2000), toAsset: 'USD' },
        { fromAsset: 'BTC', price: bigNumberify(50000), toAsset: 'USD' },
      ];
      vi.mocked(fetchLatestPrices).mockResolvedValue(manualPrices);

      const filter = ref<string | undefined>('ETH');
      const { items, getLatestPrices } = useLatestPrices(t as ReturnType<typeof useI18n>['t'], filter);
      await getLatestPrices();

      const result = get(items);
      expect(result).toHaveLength(1);
      expect(result[0].fromAsset).toBe('ETH');
    });

    it('returns all items when filter is undefined', async () => {
      setupPrices('USD', {}, { ETH: 2000, BTC: 50000 });

      const { useAssetPricesApi } = await import('@/composables/api/assets/prices');
      const { fetchLatestPrices } = useAssetPricesApi();

      const manualPrices: ManualPrice[] = [
        { fromAsset: 'ETH', price: bigNumberify(2000), toAsset: 'USD' },
        { fromAsset: 'BTC', price: bigNumberify(50000), toAsset: 'USD' },
      ];
      vi.mocked(fetchLatestPrices).mockResolvedValue(manualPrices);

      const { items, getLatestPrices } = useLatestPrices(t as ReturnType<typeof useI18n>['t']);
      await getLatestPrices();

      expect(get(items)).toHaveLength(2);
    });
  });
});
