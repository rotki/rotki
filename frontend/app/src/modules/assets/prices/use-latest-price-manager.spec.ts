import type { ManualPrice } from '@/modules/assets/prices/price-types';
import { bigNumberify } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { runSpecWith } from '@test/utils/mocks/native-task';
import { err } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { useLatestPrices } from '@/modules/assets/prices/use-latest-price-manager';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { TaskFailed } from '@/modules/core/tasks/task-result';

const { spies } = vi.hoisted(() => ({
  spies: {
    notifyError: vi.fn(),
    showErrorMessage: vi.fn(),
    submitTask: vi.fn(),
  },
}));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: (): object => ({ submitTask: spies.submitTask }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: (): object => ({ notifyError: spies.notifyError, showErrorMessage: spies.showErrorMessage }),
}));

vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: vi.fn().mockReturnValue({
    addLatestPrice: vi.fn().mockResolvedValue(true),
    deleteLatestPrice: vi.fn().mockResolvedValue(true),
    fetchLatestPrices: vi.fn().mockResolvedValue([]),
  }),
}));

vi.mock('@/modules/assets/prices/use-price-refresh', () => ({
  usePriceRefresh: vi.fn().mockReturnValue({
    refreshPrices: vi.fn().mockResolvedValue(undefined),
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
    it('should compute usdPrice in current currency without double conversion, since prices arrive already in it', async () => {
      setupPrices('EUR', { EUR: 0.85 }, { ETH: 1700 });

      const { useAssetPricesApi } = await import('@/modules/assets/api/use-asset-prices-api');
      const { fetchLatestPrices } = useAssetPricesApi();

      const manualPrices: ManualPrice[] = [
        { fromAsset: 'ETH', price: bigNumberify(123), toAsset: 'EUR' },
      ];
      vi.mocked(fetchLatestPrices).mockResolvedValue(manualPrices);

      const { items, getLatestPrices } = useLatestPrices(t);
      await getLatestPrices();

      const result = get(items);
      expect(result).toHaveLength(1);
      // ETH price is already stored in EUR (1700), no conversion needed
      expect(result[0].usdPrice.toNumber()).toBe(1700);
    });

    it('should compute usdPrice correctly when main currency is USD', async () => {
      setupPrices('USD', {}, { ETH: 2000 });

      const { useAssetPricesApi } = await import('@/modules/assets/api/use-asset-prices-api');
      const { fetchLatestPrices } = useAssetPricesApi();

      const manualPrices: ManualPrice[] = [
        { fromAsset: 'ETH', price: bigNumberify(2000), toAsset: 'USD' },
      ];
      vi.mocked(fetchLatestPrices).mockResolvedValue(manualPrices);

      const { items, getLatestPrices } = useLatestPrices(t);
      await getLatestPrices();

      const result = get(items);
      expect(result).toHaveLength(1);
      // USD is the main currency, ETH price is 2000, no conversion needed
      expect(result[0].usdPrice.toNumber()).toBe(2000);
    });

    it('should filter items when filter is provided', async () => {
      setupPrices('USD', {}, { ETH: 2000, BTC: 50000 });

      const { useAssetPricesApi } = await import('@/modules/assets/api/use-asset-prices-api');
      const { fetchLatestPrices } = useAssetPricesApi();

      const manualPrices: ManualPrice[] = [
        { fromAsset: 'ETH', price: bigNumberify(2000), toAsset: 'USD' },
        { fromAsset: 'BTC', price: bigNumberify(50000), toAsset: 'USD' },
      ];
      vi.mocked(fetchLatestPrices).mockResolvedValue(manualPrices);

      const filter = ref<string | undefined>('ETH');
      const { items, getLatestPrices } = useLatestPrices(t, filter);
      await getLatestPrices();

      const result = get(items);
      expect(result).toHaveLength(1);
      expect(result[0].fromAsset).toBe('ETH');
    });

    it('should return all items when filter is undefined', async () => {
      setupPrices('USD', {}, { ETH: 2000, BTC: 50000 });

      const { useAssetPricesApi } = await import('@/modules/assets/api/use-asset-prices-api');
      const { fetchLatestPrices } = useAssetPricesApi();

      const manualPrices: ManualPrice[] = [
        { fromAsset: 'ETH', price: bigNumberify(2000), toAsset: 'USD' },
        { fromAsset: 'BTC', price: bigNumberify(50000), toAsset: 'USD' },
      ];
      vi.mocked(fetchLatestPrices).mockResolvedValue(manualPrices);

      const { items, getLatestPrices } = useLatestPrices(t);
      await getLatestPrices();

      expect(get(items)).toHaveLength(2);
    });

    it('should price an nft through the asset it is priced in', async () => {
      setupPrices('USD', {}, { ETH: 2000 });
      vi.mocked(useAssetPricesApi().fetchLatestPrices).mockResolvedValue([
        { fromAsset: '_nft_0xabc_1', price: bigNumberify(2), toAsset: 'ETH' },
      ]);

      const { items, getLatestPrices } = useLatestPrices(t);
      await getLatestPrices();

      expect(get(items)[0].usdPrice).toEqual(bigNumberify(4000));
    });
  });

  describe('changes', () => {
    const api = useAssetPricesApi();
    const { refreshPrices } = usePriceRefresh();
    const payload = { fromAsset: 'ETH', price: '2000', toAsset: 'USD' };

    beforeEach(() => {
      vi.clearAllMocks();
      spies.submitTask.mockImplementation(runSpecWith(vi.fn()));
      vi.mocked(api.fetchLatestPrices).mockResolvedValue([]);
    });

    it('should report a price list that cannot be read and stop loading', async () => {
      vi.mocked(api.fetchLatestPrices).mockRejectedValue(new Error('offline'));

      const { getLatestPrices, loading } = useLatestPrices(t);
      await getLatestPrices();

      expect(spies.notifyError).toHaveBeenCalledOnce();
      expect(spies.notifyError.mock.calls[0][0]).toBe('price_table.fetch.failure.title');
      expect(get(loading)).toBe(false);
    });

    it('should refresh every priced asset except usd, plus the extra ones', async () => {
      vi.mocked(api.fetchLatestPrices).mockResolvedValue([
        { fromAsset: 'ETH', price: bigNumberify(2000), toAsset: 'USD' },
        { fromAsset: 'BTC', price: bigNumberify(1), toAsset: 'EUR' },
      ]);

      const { refreshCurrentPrices, refreshing } = useLatestPrices(t);
      await refreshCurrentPrices(['DAI']);

      expect(refreshPrices).toHaveBeenCalledExactlyOnceWith(false, ['ETH', 'BTC', 'EUR', 'DAI']);
      expect(get(refreshing)).toBe(false);
    });

    it('should delete the price of its asset, then refresh that asset along with the rest', async () => {
      vi.mocked(api.fetchLatestPrices).mockResolvedValue([
        { fromAsset: 'BTC', price: bigNumberify(1), toAsset: 'EUR' },
      ]);

      const { deletePrice } = useLatestPrices(t);
      await deletePrice({ fromAsset: 'ETH' });

      expect(api.deleteLatestPrice).toHaveBeenCalledExactlyOnceWith('ETH');
      expect(refreshPrices).toHaveBeenCalledExactlyOnceWith(false, ['BTC', 'EUR', 'ETH']);
      expect(spies.notifyError).not.toHaveBeenCalled();
    });

    it('should report a failed delete and leave the prices as they are', async () => {
      spies.submitTask.mockResolvedValue(err(TaskFailed({ message: 'locked' })));

      const { deletePrice } = useLatestPrices(t);
      await deletePrice({ fromAsset: 'ETH' });

      expect(spies.notifyError).toHaveBeenCalledOnce();
      expect(spies.notifyError.mock.calls[0][0]).toBe('price_table.delete.failure.title');
      expect(api.fetchLatestPrices).not.toHaveBeenCalled();
      expect(refreshPrices).not.toHaveBeenCalled();
    });

    it('should save the price and report it saved', async () => {
      const { save } = useLatestPrices(t);

      await expect(save(payload, false)).resolves.toBe(true);
      expect(api.addLatestPrice).toHaveBeenCalledExactlyOnceWith(payload);
    });

    it('should report a failed add as an add', async () => {
      spies.submitTask.mockResolvedValue(err(TaskFailed({ message: 'bad pair' })));
      const { save } = useLatestPrices(t);

      await expect(save(payload, false)).resolves.toBe(false);
      expect(spies.showErrorMessage).toHaveBeenCalledExactlyOnceWith(
        'price_management.add.error.title',
        'price_management.add.error.description',
      );
    });

    it('should report a failed edit as an edit', async () => {
      spies.submitTask.mockResolvedValue(err(TaskFailed({ message: 'bad pair' })));
      const { save } = useLatestPrices(t);

      await expect(save(payload, true)).resolves.toBe(false);
      expect(spies.showErrorMessage).toHaveBeenCalledExactlyOnceWith(
        'price_management.edit.error.title',
        'price_management.edit.error.description',
      );
    });
  });
});
