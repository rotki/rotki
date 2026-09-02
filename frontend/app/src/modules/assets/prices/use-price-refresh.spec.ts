import { bigNumberify, Blockchain } from '@rotki/common';
import { createTestBalance, createTestManualBalance, createTestPriceInfo } from '@test/utils/create-data';
import { updateGeneralSettings } from '@test/utils/general-settings';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type EffectScope } from 'vue';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { TRADE_LOCATION_BANKS } from '@/modules/core/common/defaults';
import '@test/i18n';

const mockFetchExchangeRates = vi.fn();
const mockFetchPrices = vi.fn();

vi.mock('@/modules/assets/prices/use-price-task-manager', (): any => ({
  usePriceTaskManager: () => ({
    fetchExchangeRates: mockFetchExchangeRates,
    fetchPrices: mockFetchPrices,
  }),
}));

type PriceRefresh = ReturnType<typeof import('@/modules/assets/prices/use-price-refresh').usePriceRefresh>;

const scopes: EffectScope[] = [];

async function createPriceRefresh(): Promise<PriceRefresh> {
  const { usePriceRefresh } = await import('@/modules/assets/prices/use-price-refresh');
  const scope = effectScope();
  scopes.push(scope);
  return scope.run(() => usePriceRefresh())!;
}

describe('usePriceRefresh', () => {
  beforeEach(() => {
    vi.resetModules();
    setActivePinia(createPinia());

    mockFetchExchangeRates.mockClear().mockResolvedValue({});
    mockFetchPrices.mockClear().mockResolvedValue({});
  });

  afterEach(() => {
    while (scopes.length > 0)
      scopes.pop()?.stop();
  });

  describe('adjustPrices', () => {
    it('should handle currency conversion without breaking calculations', async () => {
      const { exchangeBalances } = storeToRefs(useBalancesStore());
      const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
      const { adjustPrices } = await createPriceRefresh();

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

      adjustPrices(get(prices));

      const { prices: adjustedPrices } = storeToRefs(useBalancePricesStore());
      const pricesAfterAdjustment = get(adjustedPrices);

      expect(pricesAfterAdjustment.BTC?.value).toEqual(bigNumberify(40000));
      expect(pricesAfterAdjustment.DAI?.value).toEqual(bigNumberify(1));
      expect(pricesAfterAdjustment.ETH?.value).toEqual(bigNumberify(3000));
      expect(pricesAfterAdjustment.EUR?.value).toEqual(bigNumberify(1));
      expect(pricesAfterAdjustment.SAI?.value).toEqual(bigNumberify(1));
    });

    it('should update balances correctly when called with new prices', async () => {
      const { adjustPrices } = await createPriceRefresh();
      const { exchangeBalances } = storeToRefs(useBalancesStore());

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

      const updatedBalances = get(exchangeBalances);
      expect(updatedBalances.kraken.BTC.amount).toEqual(bigNumberify(1));
      expect(updatedBalances.kraken.ETH.amount).toEqual(bigNumberify(2));
    });

    it('should keep the previously stored prices when adjusted with an empty object', async () => {
      const { adjustPrices } = await createPriceRefresh();
      const { prices } = storeToRefs(useBalancePricesStore());

      set(prices, {
        BTC: createTestPriceInfo(40000),
      });

      adjustPrices({});

      const updatedPrices = get(prices);
      expect(updatedPrices.BTC?.value).toEqual(bigNumberify(40000));
    });
  });

  describe('refreshPrice', () => {
    it('should handle single asset price refresh', async () => {
      const { refreshPrice } = await createPriceRefresh();

      await expect(refreshPrice('BTC')).resolves.not.toThrow();
    });
  });

  describe('refreshPrices, seeded assets', () => {
    it('should refresh seeded assets even when aggregated balances are empty', async () => {
      const { prices } = storeToRefs(useBalancePricesStore());
      set(prices, {
        BTC: createTestPriceInfo(40000),
        ETH: createTestPriceInfo(3000),
      });

      const { refreshPrices } = await createPriceRefresh();
      await refreshPrices(true);

      expect(mockFetchExchangeRates).toHaveBeenCalled();
      expect(mockFetchPrices).toHaveBeenCalledTimes(1);
      const { ignoreCache, selectedAssets } = mockFetchPrices.mock.calls[0][0];
      expect(ignoreCache).toBe(true);
      expect([...selectedAssets].sort()).toEqual(['BTC', 'ETH']);
    });

    it('should union aggregated assets with seeded prices when no selection is passed', async () => {
      const { prices } = storeToRefs(useBalancePricesStore());
      const { manualBalances } = storeToRefs(useBalancesStore());

      set(manualBalances, [
        createTestManualBalance('DAI', 50, 50, TRADE_LOCATION_BANKS),
      ]);
      set(prices, {
        BTC: createTestPriceInfo(40000),
      });

      const { refreshPrices } = await createPriceRefresh();
      await refreshPrices(true);

      expect(mockFetchPrices).toHaveBeenCalledTimes(1);
      const { selectedAssets } = mockFetchPrices.mock.calls[0][0];
      expect([...selectedAssets].sort()).toEqual(['BTC', 'DAI']);
    });

    it('should respect an explicit selectedAssets list and not union with priced assets', async () => {
      const { prices } = storeToRefs(useBalancePricesStore());
      set(prices, {
        BTC: createTestPriceInfo(40000),
        ETH: createTestPriceInfo(3000),
      });

      const { refreshPrices } = await createPriceRefresh();
      await refreshPrices(true, ['DAI']);

      expect(mockFetchPrices).toHaveBeenCalledTimes(1);
      const { selectedAssets } = mockFetchPrices.mock.calls[0][0];
      expect([...selectedAssets]).toEqual(['DAI']);
    });
  });

  describe('queue fifo', () => {
    let executionOrder: string[];
    let callCount: number;
    let processingCount: number;
    let maxConcurrent: number;

    beforeEach(() => {
      executionOrder = [];
      callCount = 0;
      processingCount = 0;
      maxConcurrent = 0;
    });

    it('should process price refresh requests sequentially in FIFO order', async () => {
      const { refreshPrice, refreshPrices } = await createPriceRefresh();

      mockFetchPrices.mockImplementation(async (params: any) => {
        executionOrder.push(params.selectedAssets.join(','));
        return {};
      });

      const promise1 = refreshPrice('BTC');
      const promise2 = refreshPrices(false, ['ETH', 'DAI']);
      const promise3 = refreshPrice('USDT');

      await Promise.all([promise1, promise2, promise3]);

      expect(executionOrder).toEqual(['BTC', 'ETH,DAI', 'USDT']);
    });

    it('should handle errors in queue without breaking subsequent tasks', async () => {
      const { refreshPrice } = await createPriceRefresh();

      const FAILING_CALL = 2;
      mockFetchPrices.mockImplementation(async () => {
        callCount++;
        if (callCount === FAILING_CALL) {
          return Promise.reject(new Error('Network error'));
        }
        return Promise.resolve({});
      });

      await expect(refreshPrice('BTC')).resolves.not.toThrow();
      await expect(refreshPrice('ETH')).rejects.toThrow('Network error');
      await expect(refreshPrice('DAI')).resolves.not.toThrow();
    });

    it('should not start multiple queue processors simultaneously', async () => {
      const FETCH_DURATION_MS = 20;
      const QUEUED_ASSETS = ['BTC', 'ETH', 'DAI', 'USDT'];

      const { refreshPrices } = await createPriceRefresh();
      vi.useFakeTimers();

      mockFetchPrices.mockImplementation(async () => {
        processingCount++;
        maxConcurrent = Math.max(maxConcurrent, processingCount);

        return new Promise<Record<string, never>>((resolve) => {
          setTimeout(() => {
            processingCount--;
            resolve({});
          }, FETCH_DURATION_MS);
        });
      });

      const promises = QUEUED_ASSETS.map(async asset => refreshPrices(false, [asset]));

      for (let drained = 0; drained < QUEUED_ASSETS.length; drained++) {
        await vi.advanceTimersByTimeAsync(FETCH_DURATION_MS);
        await flushPromises();
      }

      await Promise.all(promises);
      vi.useRealTimers();

      expect(maxConcurrent).toBe(1);
    });
  });
});
