import { CURRENCY_USD, useCurrencies } from '@/types/currencies';
import { PriceOracle } from '@/types/price-oracle';
import { bigNumberify } from '@/utils/bignumbers';
import { updateGeneralSettings } from '../../../utils/general-settings';

vi.mock('@/store/tasks', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    isTaskRunning: vi.fn().mockReturnValue(false),
    awaitTask: vi.fn().mockResolvedValue({})
  })
}));

describe('store::balances/manual', () => {
  setActivePinia(createPinia());
  const store: ReturnType<typeof useBalancePricesStore> =
    useBalancePricesStore();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchPrices', () => {
    test('first call', async () => {
      const mockPricesResponse = {
        assets: {
          DAI: [1, 0, false]
        },
        targetAsset: CURRENCY_USD,
        oracles: {
          [PriceOracle.COINGECKO]: 0,
          [PriceOracle.MANUALCURRENT]: 1
        }
      };

      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: mockPricesResponse,
        meta: { title: '' }
      });

      await store.fetchPrices({
        ignoreCache: false,
        selectedAssets: ['DAI']
      });

      expect(usePriceApi().queryPrices).toHaveBeenCalledWith(
        ['DAI'],
        CURRENCY_USD,
        false
      );

      const { prices } = storeToRefs(store);
      expect(get(prices)).toMatchObject({
        DAI: {
          value: bigNumberify(1),
          isManualPrice: false,
          isCurrentCurrency: false
        }
      });
    });

    test('second call', async () => {
      const mockPricesResponse = {
        assets: {
          ETH: [2, 1, true]
        },
        targetAsset: CURRENCY_USD,
        oracles: {
          [PriceOracle.COINGECKO]: 0,
          [PriceOracle.MANUALCURRENT]: 1
        }
      };

      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: mockPricesResponse,
        meta: { title: '' }
      });

      await store.fetchPrices({
        ignoreCache: false,
        selectedAssets: ['ETH']
      });

      expect(usePriceApi().queryPrices).toHaveBeenCalledWith(
        ['ETH'],
        CURRENCY_USD,
        false
      );

      const { prices } = storeToRefs(store);
      expect(get(prices)).toMatchObject({
        DAI: {
          value: bigNumberify(1),
          isManualPrice: false,
          isCurrentCurrency: false
        },
        ETH: {
          value: bigNumberify(2),
          isManualPrice: true,
          isCurrentCurrency: true
        }
      });
    });
  });

  describe('updateBalancesPrices', () => {
    test('default', () => {
      const newBalances = store.updateBalancesPrices({
        DAI: {
          amount: bigNumberify(10),
          usdValue: bigNumberify(0)
        },
        ETH: {
          amount: bigNumberify(10),
          usdValue: bigNumberify(10)
        }
      });

      expect(newBalances).toMatchObject({
        DAI: {
          amount: bigNumberify(10),
          usdValue: bigNumberify(10)
        },
        ETH: {
          amount: bigNumberify(10),
          usdValue: bigNumberify(20)
        }
      });
    });
  });

  describe('fetchExchangeRates', () => {
    test('default', async () => {
      const mockExchangeRatesResponse = {
        EUR: 1.5
      };

      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: mockExchangeRatesResponse,
        meta: { title: '' }
      });

      await store.fetchExchangeRates();

      expect(usePriceApi().queryFiatExchangeRates).toHaveBeenCalledOnce();

      const { exchangeRates } = storeToRefs(store);
      expect(get(exchangeRates)).toMatchObject({
        EUR: bigNumberify(1.5)
      });
    });
  });

  describe('exchangeRate', () => {
    test('price is found', () => {
      expect(get(store.exchangeRate('EUR'))).toEqual(bigNumberify(1.5));
    });

    test('price is not found ', () => {
      expect(get(store.exchangeRate('JPY'))).toEqual(undefined);
    });
  });

  describe('getHistoricPrice', () => {
    const timestamp = 1669622166435;

    test('success', async () => {
      const mockResponse = {
        DAI: {
          [timestamp]: '10'
        }
      };

      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: { assets: mockResponse, targetAsset: 'USD' },
        meta: { title: '' }
      });

      const price = await store.getHistoricPrice({
        fromAsset: 'DAI',
        toAsset: 'USD',
        timestamp
      });

      expect(usePriceApi().queryHistoricalRate).toHaveBeenCalledWith(
        'DAI',
        'USD',
        timestamp
      );

      expect(price).toEqual(bigNumberify(10));
    });

    test('failed', async () => {
      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: { assets: {}, targetAsset: 'USD' },
        meta: { title: '' }
      });

      const price = await store.getHistoricPrice({
        fromAsset: 'DAI',
        toAsset: 'USD',
        timestamp
      });

      expect(price).toEqual(bigNumberify(-1));
    });
  });

  describe('toSelectedCurrency', () => {
    test('default', () => {
      const { findCurrency } = useCurrencies();
      updateGeneralSettings({ mainCurrency: findCurrency('EUR') });

      const convertedValue = store.toSelectedCurrency(bigNumberify(10));

      expect(get(convertedValue)).toEqual(bigNumberify(15));
    });
  });

  describe('assetPrice', () => {
    test('price is found', () => {
      expect(get(store.assetPrice('DAI'))).toEqual(bigNumberify(1));
    });

    test('price is not found', () => {
      expect(get(store.assetPrice('BTC'))).toEqual(undefined);
    });
  });

  describe('isManualAssetPrice', () => {
    test('default', () => {
      expect(get(store.isManualAssetPrice('DAI'))).toEqual(false);
      expect(get(store.isManualAssetPrice('ETH'))).toEqual(true);
    });
  });

  describe('isAssetPriceInCurrentCurrency', () => {
    test('default', () => {
      expect(get(store.isAssetPriceInCurrentCurrency('DAI'))).toEqual(false);
      expect(get(store.isAssetPriceInCurrentCurrency('ETH'))).toEqual(true);
    });
  });
});
