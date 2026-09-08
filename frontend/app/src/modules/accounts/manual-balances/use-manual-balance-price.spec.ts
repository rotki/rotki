import { type BigNumber, bigNumberify, Zero } from '@rotki/common';
import { flushPromises } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useManualBalancePrice } from '@/modules/accounts/manual-balances/use-manual-balance-price';

const addLatestPrice = vi.fn<(payload: { fromAsset: string; price: string; toAsset: string }) => Promise<boolean>>();
const fetchLatestPrices = vi.fn<(payload: { fromAsset: string }) => Promise<{ price: BigNumber; toAsset: string }[]>>();
const fetchPrices = vi.fn(async (): Promise<void> => Promise.resolve());
const getAssetPrice = vi.fn<(asset: string) => BigNumber | undefined>();

vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: (): Record<string, unknown> => ({ addLatestPrice, fetchLatestPrices }),
}));

vi.mock('@/modules/assets/prices/use-price-task-manager', () => ({
  usePriceTaskManager: (): Record<string, unknown> => ({ fetchPrices }),
}));

vi.mock('@/modules/assets/prices/use-price-utils', () => ({
  usePriceUtils: (): Record<string, unknown> => ({ getAssetPrice }),
}));

describe('useManualBalancePrice', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchLatestPrices.mockResolvedValue([]);
    getAssetPrice.mockReturnValue(undefined);
    addLatestPrice.mockResolvedValue(true);
  });

  describe('looking a price up', () => {
    it('should use a price the user saved before', async () => {
      fetchLatestPrices.mockResolvedValue([{ price: bigNumberify('42'), toAsset: 'EUR' }]);
      const { modelPrice, modelPriceAsset } = useManualBalancePrice('ETH', 'EUR');
      await flushPromises();

      expect(get(modelPrice)).toBe('42');
      expect(get(modelPriceAsset)).toBe('EUR');
    });

    /** An asset priced in the main currency is worth exactly one of it. */
    it('should price the main currency at one of itself', async () => {
      const { modelPrice, modelPriceAsset } = useManualBalancePrice('EUR', 'EUR');
      await flushPromises();

      expect(get(modelPrice)).toBe('1');
      expect(get(modelPriceAsset)).toBe('EUR');
      expect(fetchPrices).not.toHaveBeenCalled();
    });

    it('should fall back to the oracle price in the main currency', async () => {
      getAssetPrice.mockReturnValue(bigNumberify('1500'));
      const { modelPrice, modelPriceAsset } = useManualBalancePrice('ETH', 'EUR');
      await flushPromises();

      expect(get(modelPrice)).toBe('1500');
      expect(get(modelPriceAsset)).toBe('EUR');
    });

    it('should leave the fields blank when no price can be found', async () => {
      const { modelIsCustomPrice, modelPrice } = useManualBalancePrice('ETH', 'EUR');
      await flushPromises();

      expect(get(modelPrice)).toBe('');
      expect(get(modelIsCustomPrice)).toBe(true);
    });

    /** A zero oracle price is no price at all, not a valuation of nothing. */
    it('should treat a zero oracle price as no price', async () => {
      getAssetPrice.mockReturnValue(Zero);
      const { modelIsCustomPrice, modelPrice } = useManualBalancePrice('ETH', 'EUR');
      await flushPromises();

      expect(get(modelPrice)).toBe('');
      expect(get(modelIsCustomPrice)).toBe(true);
    });

    it('should look nothing up without an asset', async () => {
      const { modelPrice } = useManualBalancePrice('', 'EUR');
      await flushPromises();

      expect(get(modelPrice)).toBe('');
      expect(fetchLatestPrices).not.toHaveBeenCalled();
    });

    it('should look the price up again when the asset changes', async () => {
      const asset = ref('ETH');
      useManualBalancePrice(asset, 'EUR');
      await flushPromises();

      set(asset, 'BTC');
      await flushPromises();

      expect(fetchLatestPrices).toHaveBeenLastCalledWith({ fromAsset: 'BTC' });
    });
  });

  describe('the fiat hint', () => {
    it('should show the fiat value for a price quoted in something else', async () => {
      fetchLatestPrices.mockResolvedValue([{ price: bigNumberify('1'), toAsset: 'BTC' }]);
      getAssetPrice.mockReturnValue(bigNumberify('1500'));
      const { fiatPriceHint } = useManualBalancePrice('ETH', 'EUR');
      await flushPromises();

      expect(get(fiatPriceHint)?.toFixed()).toBe('1500');
    });

    it('should show no hint for a price already in the main currency', async () => {
      fetchLatestPrices.mockResolvedValue([{ price: bigNumberify('42'), toAsset: 'EUR' }]);
      const { fiatPriceHint } = useManualBalancePrice('ETH', 'EUR');
      await flushPromises();

      expect(get(fiatPriceHint)).toBeNull();
      expect(fetchPrices).not.toHaveBeenCalled();
    });
  });

  describe('entering a price by hand', () => {
    it('should empty the fields when the toggle goes on', async () => {
      getAssetPrice.mockReturnValue(bigNumberify('1500'));
      const { modelIsCustomPrice, modelPrice, modelPriceAsset } = useManualBalancePrice('ETH', 'EUR');
      await flushPromises();

      set(modelIsCustomPrice, true);
      await flushPromises();

      expect(get(modelPrice)).toBe('');
      expect(get(modelPriceAsset)).toBe('');
    });

    it('should look the price up again when the toggle goes off', async () => {
      getAssetPrice.mockReturnValue(bigNumberify('1500'));
      const { modelIsCustomPrice } = useManualBalancePrice('ETH', 'EUR');
      await flushPromises();
      set(modelIsCustomPrice, true);
      await flushPromises();
      fetchLatestPrices.mockClear();

      set(modelIsCustomPrice, false);
      await flushPromises();

      expect(fetchLatestPrices).toHaveBeenCalledWith({ fromAsset: 'ETH' });
    });
  });

  describe('saving a price', () => {
    it('should save what the user typed', async () => {
      const { modelIsCustomPrice, modelPrice, modelPriceAsset, savePrice } = useManualBalancePrice('ETH', 'EUR');
      await flushPromises();
      set(modelIsCustomPrice, true);
      set(modelPrice, '99');
      set(modelPriceAsset, 'EUR');

      expect(await savePrice('ETH')).toBe(true);
      expect(addLatestPrice).toHaveBeenCalledWith({ fromAsset: 'ETH', price: '99', toAsset: 'EUR' });
    });

    /** A price the app found is already known, so re-saving it would add a custom price nobody asked for. */
    it('should not save a price the lookup found', async () => {
      getAssetPrice.mockReturnValue(bigNumberify('1500'));
      const { savePrice } = useManualBalancePrice('ETH', 'EUR');
      await flushPromises();

      expect(await savePrice('ETH')).toBe(false);
      expect(addLatestPrice).not.toHaveBeenCalled();
    });

    it('should not save without a price', async () => {
      const { modelIsCustomPrice, modelPriceAsset, savePrice } = useManualBalancePrice('ETH', 'EUR');
      await flushPromises();
      set(modelIsCustomPrice, true);
      set(modelPriceAsset, 'EUR');

      expect(await savePrice('ETH')).toBe(false);
      expect(addLatestPrice).not.toHaveBeenCalled();
    });

    it('should not save without a price asset', async () => {
      const { modelIsCustomPrice, modelPrice, savePrice } = useManualBalancePrice('ETH', 'EUR');
      await flushPromises();
      set(modelIsCustomPrice, true);
      set(modelPrice, '99');

      expect(await savePrice('ETH')).toBe(false);
      expect(addLatestPrice).not.toHaveBeenCalled();
    });
  });
});
