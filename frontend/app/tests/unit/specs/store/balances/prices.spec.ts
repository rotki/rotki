import { usePriceApi } from '@/composables/api/balances/price';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useTaskStore } from '@/store/tasks';
import { CURRENCY_USD, useCurrencies } from '@/types/currencies';
import { PriceOracle } from '@/types/settings/price-oracle';
import { bigNumberify } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { updateGeneralSettings } from '../../../utils/general-settings';

vi.mock('@/store/tasks', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    isTaskRunning: vi.fn().mockReturnValue(false),
    awaitTask: vi.fn().mockResolvedValue({}),
  }),
}));

describe('store::balances/manual', () => {
  setActivePinia(createPinia());
  const store: ReturnType<typeof useBalancePricesStore> = useBalancePricesStore();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchPrices', () => {
    it('first call', async () => {
      const mockPricesResponse = {
        assets: {
          DAI: [1, 0],
        },
        targetAsset: CURRENCY_USD,
        oracles: {
          [PriceOracle.COINGECKO]: 0,
          [PriceOracle.MANUALCURRENT]: 1,
        },
      };

      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: mockPricesResponse,
        meta: { title: '' },
      });

      await store.fetchPrices({
        ignoreCache: false,
        selectedAssets: ['DAI'],
      });

      expect(usePriceApi().queryPrices).toHaveBeenCalledWith(['DAI'], CURRENCY_USD, false);

      const { prices } = storeToRefs(store);
      expect(get(prices)).toMatchObject({
        DAI: {
          value: bigNumberify(1),
          isManualPrice: false,
        },
      });
    });

    it('second call', async () => {
      const mockPricesResponse = {
        assets: {
          ETH: [2, 1],
        },
        targetAsset: CURRENCY_USD,
        oracles: {
          [PriceOracle.COINGECKO]: 0,
          [PriceOracle.MANUALCURRENT]: 1,
        },
      };

      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: mockPricesResponse,
        meta: { title: '' },
      });

      await store.fetchPrices({
        ignoreCache: false,
        selectedAssets: ['ETH'],
      });

      expect(usePriceApi().queryPrices).toHaveBeenCalledWith(['ETH'], CURRENCY_USD, false);

      const { prices } = storeToRefs(store);
      expect(get(prices)).toMatchObject({
        DAI: {
          value: bigNumberify(1),
          isManualPrice: false,
        },
        ETH: {
          value: bigNumberify(2),
          isManualPrice: true,
        },
      });
    });
  });

  describe('updateBalancesPrices', () => {
    it('default', () => {
      const newBalances = store.updateBalancesPrices({
        DAI: {
          amount: bigNumberify(10),
          usdValue: bigNumberify(0),
        },
        ETH: {
          amount: bigNumberify(10),
          usdValue: bigNumberify(10),
        },
      });

      expect(newBalances).toMatchObject({
        DAI: {
          amount: bigNumberify(10),
          usdValue: bigNumberify(10),
        },
        ETH: {
          amount: bigNumberify(10),
          usdValue: bigNumberify(20),
        },
      });
    });
  });

  describe('fetchExchangeRates', () => {
    it('default', async () => {
      const mockExchangeRatesResponse = {
        EUR: 1.5,
      };

      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: mockExchangeRatesResponse,
        meta: { title: '' },
      });

      await store.fetchExchangeRates();

      expect(usePriceApi().queryFiatExchangeRates).toHaveBeenCalledOnce();

      const { exchangeRates } = storeToRefs(store);
      expect(get(exchangeRates)).toMatchObject({
        EUR: bigNumberify(1.5),
      });
    });
  });

  describe('exchangeRate', () => {
    it('price is found', () => {
      expect(get(store.exchangeRate('EUR'))).toEqual(bigNumberify(1.5));
    });

    it('price is not found ', () => {
      expect(get(store.exchangeRate('JPY'))).toEqual(undefined);
    });
  });

  describe('getHistoricPrice', () => {
    const timestamp = 1669622166435;

    it('success', async () => {
      const mockResponse = {
        DAI: {
          [timestamp]: '10',
        },
      };

      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: { assets: mockResponse, targetAsset: 'USD' },
        meta: { title: '' },
      });

      const price = await store.getHistoricPrice({
        fromAsset: 'DAI',
        toAsset: 'USD',
        timestamp,
      });

      expect(usePriceApi().queryHistoricalRate).toHaveBeenCalledWith('DAI', 'USD', timestamp);

      expect(price).toEqual(bigNumberify(10));
    });

    it('failed', async () => {
      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: { assets: {}, targetAsset: 'USD' },
        meta: { title: '' },
      });

      const price = await store.getHistoricPrice({
        fromAsset: 'DAI',
        toAsset: 'USD',
        timestamp,
      });

      expect(price).toEqual(bigNumberify(-1));
    });
  });

  describe('toSelectedCurrency', () => {
    it('default', () => {
      const { findCurrency } = useCurrencies();
      updateGeneralSettings({ mainCurrency: findCurrency('EUR') });

      const convertedValue = store.toSelectedCurrency(bigNumberify(10));

      expect(get(convertedValue)).toEqual(bigNumberify(15));
    });
  });

  describe('assetPrice', () => {
    it('price is found', () => {
      expect(get(store.assetPrice('DAI'))).toEqual(bigNumberify(1));
    });

    it('price is not found', () => {
      expect(get(store.assetPrice('BTC'))).toEqual(undefined);
    });
  });

  describe('isManualAssetPrice', () => {
    it('default', () => {
      expect(get(store.isManualAssetPrice('DAI'))).toEqual(false);
      expect(get(store.isManualAssetPrice('ETH'))).toEqual(true);
    });
  });

  describe('isAssetPriceInCurrentCurrency', () => {
    it('default', () => {
      expect(get(store.isAssetPriceInCurrentCurrency('DAI'))).toEqual(false);
      expect(get(store.isAssetPriceInCurrentCurrency('ETH'))).toEqual(false);
    });
  });
});
