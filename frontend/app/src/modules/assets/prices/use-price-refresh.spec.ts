import type { FetchPricePayload } from '@/modules/accounts/blockchain-accounts';
import { bigNumberify, Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { createTestBalance, createTestManualBalance, createTestPriceInfo } from '@test/utils/create-data';
import { updateGeneralSettings } from '@test/utils/general-settings';
import flushPromises from 'flush-promises';
import { ok } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type EffectScope } from 'vue';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { TRADE_LOCATION_BANKS } from '@/modules/core/common/defaults';
import '@test/i18n';

const mockRefreshLatestPrices = vi.fn<(payload: FetchPricePayload, onFetched: () => void) => Promise<void>>();

vi.mock('@/modules/assets/prices/use-price-task-manager', () => ({
  usePriceTaskManager: (): { refreshLatestPrices: typeof mockRefreshLatestPrices } => ({
    refreshLatestPrices: mockRefreshLatestPrices,
  }),
}));

/** The payload of the only refresh asked for. */
function refreshedWith(): FetchPricePayload {
  expect(mockRefreshLatestPrices).toHaveBeenCalledOnce();
  return mockRefreshLatestPrices.mock.calls[0][0];
}

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

    mockRefreshLatestPrices.mockReset().mockImplementation(async (_payload, onFetched) => {
      onFetched();
    });
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
    it('should refresh the one asset, bypassing the cache', async () => {
      const { refreshPrice } = await createPriceRefresh();

      await refreshPrice('BTC');

      expect(refreshedWith()).toStrictEqual({ ignoreCache: true, selectedAssets: ['BTC'] });
    });
  });

  describe('applying the prices', () => {
    it('should write the fetched prices into the balances once the refresh fetched them', async () => {
      const balances = useBalancesStore();
      const updatePrices = vi.spyOn(balances, 'updatePrices');
      const { refreshPrices } = await createPriceRefresh();

      await refreshPrices(false, ['BTC']);

      expect(updatePrices).toHaveBeenCalledOnce();
    });

    it('should not apply anything when the refresh never fetched, as when it was cancelled', async () => {
      mockRefreshLatestPrices.mockImplementation(async () => {});
      const balances = useBalancesStore();
      const updatePrices = vi.spyOn(balances, 'updatePrices');
      const { refreshPrices } = await createPriceRefresh();

      await refreshPrices(false, ['BTC']);

      expect(updatePrices).not.toHaveBeenCalled();
    });

    it('should apply the stored prices without a refresh when there is nothing to fetch', async () => {
      const balances = useBalancesStore();
      const updatePrices = vi.spyOn(balances, 'updatePrices');
      const { refreshPrices } = await createPriceRefresh();

      await refreshPrices(false, []);

      expect(mockRefreshLatestPrices).not.toHaveBeenCalled();
      expect(updatePrices).toHaveBeenCalledOnce();
    });

    it('should still refresh with nothing to price when bypassing the cache, for the exchange rates', async () => {
      const { refreshPrices } = await createPriceRefresh();

      await refreshPrices(true, []);

      expect(refreshedWith()).toStrictEqual({ ignoreCache: true, selectedAssets: [] });
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

      const { ignoreCache, selectedAssets } = refreshedWith();
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

      expect([...refreshedWith().selectedAssets].sort()).toEqual(['BTC', 'DAI']);
    });

    it('should respect an explicit selectedAssets list and not union with priced assets', async () => {
      const { prices } = storeToRefs(useBalancePricesStore());
      set(prices, {
        BTC: createTestPriceInfo(40000),
        ETH: createTestPriceInfo(3000),
      });

      const { refreshPrices } = await createPriceRefresh();
      await refreshPrices(true, ['DAI']);

      expect([...refreshedWith().selectedAssets]).toEqual(['DAI']);
    });
  });

  describe('refreshing', () => {
    /** Holds one PRICES activity open under `parts` until the returned release is called. */
    async function holdPriceWork(...parts: string[]): Promise<() => void> {
      const { useNativeTask } = await import('@/modules/task-center/use-native-task');
      const { ActivityKind, makeActivityId } = await import('@/modules/task-center/core/types');
      let release = (): void => {};
      const held = new Promise<void>((resolve) => {
        release = resolve;
      });
      startPromise(useNativeTask().submitTask({
        id: makeActivityId(ActivityKind.PRICES, ...parts),
        kind: ActivityKind.PRICES,
        run: async () => {
          await held;
          return ok(undefined);
        },
        title: 'prices',
      }));
      await flushPromises();
      return release;
    }

    it.each([
      { parts: ['latest', 'digest', 'cached'], work: 'latest prices' },
      { parts: ['exchange-rates'], work: 'exchange rates' },
    ])('should report a refresh while $work are being fetched, and stop once they finish', async ({ parts }) => {
      const { refreshing } = await createPriceRefresh();
      const release = await holdPriceWork(...parts);

      expect(get(refreshing)).toBe(true);

      release();
      await flushPromises();

      expect(get(refreshing)).toBe(false);
    });

    it.each([
      { parts: ['historic', 'ETH', 'USD', '1700000000'], work: 'a historic lookup' },
      { parts: ['daily', 'ETH', 'USD'], work: 'daily prices' },
      { parts: ['oracle-cache'], work: 'the oracle cache' },
      { parts: ['manual', 'add', 'ETH'], work: 'a manual price edit' },
    ])('should not report a refresh for $work', async ({ parts }) => {
      const { refreshing } = await createPriceRefresh();
      const release = await holdPriceWork(...parts);

      expect(get(refreshing)).toBe(false);

      release();
    });
  });
});
