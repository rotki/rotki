import type { ManualPrice } from '@/modules/assets/prices/price-types';
import type { ProblemMessage } from '@/modules/core/notifications/problems/backend-problem-tree';
import { bigNumberify } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { runSpecWith } from '@test/utils/mocks/native-task';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { useLatestPrices } from '@/modules/assets/prices/use-latest-price-manager';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { useBackendProblemsStore } from '@/modules/core/notifications/problems/use-backend-problems-store';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';

const { spies } = vi.hoisted(() => ({
  spies: {
    notifyFailure: vi.fn(),
    showErrorMessage: vi.fn(),
    submitTask: vi.fn(),
  },
}));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: (): object => ({ submitTask: spies.submitTask }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: (): object => ({ notifyFailure: spies.notifyFailure, showErrorMessage: spies.showErrorMessage }),
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

function fileMissingPrice(asset: string, timestamp: number | null): void {
  const source: ProblemMessage = {
    fields: { asset, timestamp },
    group: ['warning', 'price', null, asset],
    key: 'price',
    subject: null,
    value: `no price for ${asset}`,
    verbosity: 'warning',
  };
  useBackendProblemsStore().record({ at: new Date(), count: 1, identity: JSON.stringify(source.group), source });
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

      const { items, getLatestPrices } = useLatestPrices();
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

      const { items, getLatestPrices } = useLatestPrices();
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
      const { items, getLatestPrices } = useLatestPrices(filter);
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

      const { items, getLatestPrices } = useLatestPrices();
      await getLatestPrices();

      expect(get(items)).toHaveLength(2);
    });

    it('should price an nft through the asset it is priced in', async () => {
      setupPrices('USD', {}, { ETH: 2000 });
      vi.mocked(useAssetPricesApi().fetchLatestPrices).mockResolvedValue([
        { fromAsset: '_nft_0xabc_1', price: bigNumberify(2), toAsset: 'ETH' },
      ]);

      const { items, getLatestPrices } = useLatestPrices();
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

    it('should name a price list that cannot be read in the table, filing no notification', async () => {
      vi.mocked(api.fetchLatestPrices).mockRejectedValue(new Error('offline'));

      const { emptyState, getLatestPrices, loading } = useLatestPrices();
      await getLatestPrices();

      expect(get(emptyState)).toEqual({ description: 'offline', label: 'data_table.fetch_failed' });
      expect(spies.notifyFailure).not.toHaveBeenCalled();
      expect(get(loading)).toBe(false);
    });

    it('should go back to the plain empty text once a later fetch succeeds', async () => {
      vi.mocked(api.fetchLatestPrices).mockRejectedValueOnce(new Error('offline'));
      const { emptyState, getLatestPrices } = useLatestPrices();
      await getLatestPrices();

      await getLatestPrices();

      expect(get(emptyState)).toEqual({ description: 'data_table.no_data' });
    });

    it('should refresh every priced asset except usd, plus the extra ones', async () => {
      vi.mocked(api.fetchLatestPrices).mockResolvedValue([
        { fromAsset: 'ETH', price: bigNumberify(2000), toAsset: 'USD' },
        { fromAsset: 'BTC', price: bigNumberify(1), toAsset: 'EUR' },
      ]);

      const { refreshCurrentPrices, refreshing } = useLatestPrices();
      await refreshCurrentPrices(['DAI']);

      expect(refreshPrices).toHaveBeenCalledExactlyOnceWith(false, ['ETH', 'BTC', 'EUR', 'DAI']);
      expect(get(refreshing)).toBe(false);
    });

    it('should delete the price of its asset, then refresh that asset along with the rest', async () => {
      vi.mocked(api.fetchLatestPrices).mockResolvedValue([
        { fromAsset: 'BTC', price: bigNumberify(1), toAsset: 'EUR' },
      ]);

      const { deletePrice } = useLatestPrices();
      await deletePrice({ fromAsset: 'ETH' });

      expect(api.deleteLatestPrice).toHaveBeenCalledExactlyOnceWith('ETH');
      expect(refreshPrices).toHaveBeenCalledExactlyOnceWith(false, ['BTC', 'EUR', 'ETH']);
      expect(spies.notifyFailure).not.toHaveBeenCalled();
    });

    it('should leave a failed delete to its task centre row and leave the prices as they are', async () => {
      spies.submitTask.mockResolvedValue(err(TaskFailed({ message: 'locked' })));

      const { deletePrice } = useLatestPrices();
      await deletePrice({ fromAsset: 'ETH' });

      expect(spies.submitTask).toHaveBeenCalledOnce();
      expect(spies.notifyFailure).not.toHaveBeenCalled();
      expect(api.fetchLatestPrices).not.toHaveBeenCalled();
      expect(refreshPrices).not.toHaveBeenCalled();
    });

    it('should save the price and report it saved', async () => {
      const { save } = useLatestPrices();

      await expect(save(payload)).resolves.toEqual(ok(true));
      expect(api.addLatestPrice).toHaveBeenCalledExactlyOnceWith(payload);
    });

    it('should clear the drawer\'s missing current price for the asset it saved, and no other asset\'s', async () => {
      fileMissingPrice('ETH', null);
      fileMissingPrice('BTC', null);
      const { save } = useLatestPrices();

      await save(payload);

      const fields = useBackendProblemsStore().problems.flatMap(problem => problem.items.map(item => item.source.fields));
      expect(fields).toEqual([{ asset: 'BTC', timestamp: null }]);
    });

    it('should keep a missing historic price of the asset, which a latest price does not fix', async () => {
      fileMissingPrice('ETH', 1700000000);
      const { save } = useLatestPrices();

      await save(payload);

      expect(useBackendProblemsStore().problems).toHaveLength(1);
    });

    it('should keep the missing current price when the save fails', async () => {
      spies.submitTask.mockResolvedValue(err(TaskFailed({ message: 'bad pair' })));
      fileMissingPrice('ETH', null);
      const { save } = useLatestPrices();

      await save(payload);

      expect(useBackendProblemsStore().problems).toHaveLength(1);
    });

    it('should hand a failed save back for the open form to name, instead of a message', async () => {
      const failure = TaskFailed({ message: 'bad pair' });
      spies.submitTask.mockResolvedValue(err(failure));
      const { save } = useLatestPrices();

      await expect(save(payload)).resolves.toEqual(err(failure));
      expect(spies.showErrorMessage).not.toHaveBeenCalled();
    });

    it('should hand back nothing to name when the save task was cancelled', async () => {
      spies.submitTask.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));
      const { save } = useLatestPrices();

      await expect(save(payload)).resolves.toEqual(ok(false));
    });
  });
});
