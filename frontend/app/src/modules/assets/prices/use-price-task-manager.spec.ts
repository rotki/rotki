import { bigNumberify } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { usePriceApi } from '@/modules/balances/api/use-price-api';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { PriceOracle } from '@/modules/settings/types/price-oracle';

const runTaskMock = vi.fn();

vi.mock('@/modules/core/tasks/use-task-handler', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useTaskHandler: vi.fn().mockReturnValue({
    runTask: async (taskFn: () => Promise<unknown>, ...rest: unknown[]): Promise<unknown> => {
      await taskFn();
      return runTaskMock(taskFn, ...rest);
    },
    cancelTask: vi.fn(),
    cancelTaskByTaskType: vi.fn(),
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
    runTaskMock.mockReset();
    vi.clearAllMocks();
    priceTaskManager = usePriceTaskManager();
  });

  describe('fetchPrices', () => {
    const createMockPriceResponse = (assets: Record<string, [number, number]>, targetAsset = 'USD'): PriceResponse => ({
      assets,
      oracles: {
        [PriceOracle.COINGECKO]: 0,
        [PriceOracle.MANUALCURRENT]: 1,
      },
      targetAsset,
    });

    const executeFetchPrices = async (
      assets: string[],
      mockResponse: PriceResponse,
      expectedCurrency = 'USD',
    ): Promise<void> => {
      runTaskMock.mockResolvedValue({ success: true, result: mockResponse });

      await priceTaskManager.fetchPrices({
        ignoreCache: false,
        selectedAssets: assets,
      });

      expect(usePriceApi().queryPrices).toHaveBeenCalledWith(assets, expectedCurrency, false);
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

    it('should use the selected currency symbol when fetching prices', async () => {
      const { findCurrency } = useCurrencies();
      updateGeneralSettings({ mainCurrency: findCurrency('EUR') });

      const mockPricesResponse = createMockPriceResponse({ DAI: [1, 0] }, 'EUR');

      await executeFetchPrices(['DAI'], mockPricesResponse, 'EUR');

      // Reset to USD for other tests
      updateGeneralSettings({ mainCurrency: findCurrency('USD') });
    });
  });

  it('should update exchange rates when fetchExchangeRates is called', async () => {
    const mockExchangeRatesResponse = {
      EUR: 1.5,
    };

    runTaskMock.mockResolvedValue({ success: true, result: mockExchangeRatesResponse });

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

      runTaskMock.mockResolvedValue({ success: true, result: { assets: mockResponse, targetAsset: 'USD' } });

      const price = await priceTaskManager.getHistoricPrice({
        fromAsset: 'DAI',
        timestamp,
        toAsset: 'USD',
      });

      expect(usePriceApi().queryHistoricalRate).toHaveBeenCalledWith('DAI', 'USD', timestamp);

      expect(price).toEqual(bigNumberify(10));
    });

    it('should return minus one on failure', async () => {
      runTaskMock.mockResolvedValue({ success: true, result: { assets: {}, targetAsset: 'USD' } });

      const price = await priceTaskManager.getHistoricPrice({
        fromAsset: 'DAI',
        timestamp,
        toAsset: 'USD',
      });

      expect(price).toEqual(bigNumberify(-1));
    });
  });
});
