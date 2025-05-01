import { usePriceApi } from '@/composables/api/balances/price';
import { usePriceTaskManager } from '@/modules/prices/use-price-task-manager';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useTaskStore } from '@/store/tasks';
import { CURRENCY_USD } from '@/types/currencies';
import { PriceOracle } from '@/types/settings/price-oracle';
import { bigNumberify } from '@rotki/common';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/store/tasks', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    awaitTask: vi.fn().mockResolvedValue({}),
    isTaskRunning: vi.fn().mockReturnValue(false),
  }),
}));

interface PriceResponse {
  assets: Record<string, [number, number]>;
  oracles: { coingecko: number; manualcurrent: number };
  targetAsset: string;
}
describe('usePriceTaskManager', () => {
  let store: ReturnType<typeof useBalancePricesStore>;
  let priceTaskManager: ReturnType<typeof usePriceTaskManager>;

  beforeAll(() => {
    setActivePinia(createPinia());
    store = useBalancePricesStore();
  });

  beforeEach(() => {
    vi.clearAllMocks();
    priceTaskManager = usePriceTaskManager();
  });

  describe('fetchPrices', () => {
    const createMockPriceResponse = (assets: Record<string, [number, number]>): PriceResponse => ({
      assets,
      oracles: {
        [PriceOracle.COINGECKO]: 0,
        [PriceOracle.MANUALCURRENT]: 1,
      },
      targetAsset: CURRENCY_USD,
    });

    const executeFetchPrices = async (
      assets: string[],
      mockResponse: PriceResponse,
    ): Promise<void> => {
      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        meta: { title: '' },
        result: mockResponse,
      });

      await priceTaskManager.fetchPrices({
        ignoreCache: false,
        selectedAssets: assets,
      });

      expect(usePriceApi().queryPrices).toHaveBeenCalledWith(assets, CURRENCY_USD, false);
    };

    it('should update the prices when fetchPrices is called', async () => {
      const mockPricesResponse = createMockPriceResponse({ DAI: [1, 0] });

      await executeFetchPrices(['DAI'], mockPricesResponse);

      const { prices } = storeToRefs(store);
      expect(get(prices)).toMatchObject({
        DAI: {
          isManualPrice: false,
          value: bigNumberify(1),
        },
      });
    });

    it('should append any new prices to the existing data when re-called', async () => {
      const mockPricesResponse = createMockPriceResponse({ ETH: [2, 1] });

      await executeFetchPrices(['ETH'], mockPricesResponse);

      const { prices } = storeToRefs(store);
      expect(get(prices)).toMatchObject({
        DAI: {
          isManualPrice: false,
          value: bigNumberify(1),
        },
        ETH: {
          isManualPrice: true,
          value: bigNumberify(2),
        },
      });
    });
  });

  it('should update exchange rates when fetchExchangeRates is called', async () => {
    const mockExchangeRatesResponse = {
      EUR: 1.5,
    };

    vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
      meta: { title: '' },
      result: mockExchangeRatesResponse,
    });

    await priceTaskManager.fetchExchangeRates();

    expect(usePriceApi().queryFiatExchangeRates).toHaveBeenCalledOnce();

    const { exchangeRates } = storeToRefs(store);
    expect(get(exchangeRates)).toMatchObject({
      EUR: bigNumberify(1.5),
    });
  });

  describe('getHistoricPrice', () => {
    const timestamp = 1669622166435;

    it('should return the price on success', async () => {
      const mockResponse = {
        DAI: {
          [timestamp]: '10',
        },
      };

      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        meta: { title: '' },
        result: { assets: mockResponse, targetAsset: 'USD' },
      });

      const price = await priceTaskManager.getHistoricPrice({
        fromAsset: 'DAI',
        timestamp,
        toAsset: 'USD',
      });

      expect(usePriceApi().queryHistoricalRate).toHaveBeenCalledWith('DAI', 'USD', timestamp);

      expect(price).toEqual(bigNumberify(10));
    });

    it('should return minus one on failure', async () => {
      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        meta: { title: '' },
        result: { assets: {}, targetAsset: 'USD' },
      });

      const price = await priceTaskManager.getHistoricPrice({
        fromAsset: 'DAI',
        timestamp,
        toAsset: 'USD',
      });

      expect(price).toEqual(bigNumberify(-1));
    });
  });
});
