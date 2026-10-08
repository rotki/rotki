import { bigNumberify } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { mockUseNotifications } from '@test/utils/mocks/notifications';
import { mockUseTaskHandler } from '@test/utils/mocks/task-runner';
import flushPromises from 'flush-promises';
import { err, ok } from 'plainfp/result';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { usePriceApi } from '@/modules/balances/api/use-price-api';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

const { notifyError, notifyInfo, runTaskMock } = vi.hoisted(() => ({ notifyError: vi.fn(), notifyInfo: vi.fn(), runTaskMock: vi.fn() }));

vi.mock('@/modules/core/tasks/use-task-handler', async importOriginal =>
  mockUseTaskHandler(await importOriginal<Record<string, unknown>>(), { cancelTaskById: vi.fn(async () => true), runTask: runTaskMock }));

vi.mock('@/modules/core/notifications/use-notifications', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  ...mockUseNotifications({ notifyError, notifyInfo }),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: vi.fn(() => ({ getAssetField: (asset: string): string => asset })),
}));

interface PriceResponse {
  assets: Record<string, [number, number]>;
  oracles: { coingecko: number; manualcurrent: number };
  targetAsset: string;
}
describe('usePriceTaskManager', () => {
  let store: ReturnType<typeof useBalancePricesStore>;
  let priceTaskManager: ReturnType<typeof usePriceTaskManager>;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useBalancePricesStore();
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
      runTaskMock.mockResolvedValue(ok(mockResponse));

      await priceTaskManager.fetchPrices({
        ignoreCache: false,
        selectedAssets: assets,
      });

      expect(usePriceApi().queryPrices).toHaveBeenCalledWith(assets, expectedCurrency, false);
    };

    afterEach(() => {
      const { findCurrency } = useCurrencies();
      updateGeneralSettings({ mainCurrency: findCurrency('USD') });
    });

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
      await executeFetchPrices(['DAI'], createMockPriceResponse({ DAI: [1, 0] }));
      await executeFetchPrices(['ETH'], createMockPriceResponse({ ETH: [2, 1] }));

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
    });
  });

  it('should update exchange rates when fetchExchangeRates is called', async () => {
    const mockExchangeRatesResponse = {
      EUR: 1.5,
    };

    runTaskMock.mockResolvedValue(ok(mockExchangeRatesResponse));

    await priceTaskManager.fetchExchangeRates();

    expect(usePriceApi().queryFiatExchangeRates).toHaveBeenCalledOnce();

    const { exchangeRates } = storeToRefs(store);
    expect(get(exchangeRates)).toMatchObject({
      EUR: bigNumberify(1.5),
    });
  });

  describe('refreshLatestPrices', () => {
    const priceResponse = (asset: string): Record<string, unknown> => ({
      assets: { [asset]: [1, 0] },
      oracles: { [PriceOracle.COINGECKO]: 0, [PriceOracle.MANUALCURRENT]: 1 },
      targetAsset: 'USD',
    });

    /**
     * Makes the next backend task wait until released.
     *
     * @returns `release`, which resolves the task once it has started (await it before releasing)
     */
    function holdNextTask(asset: string): { release: () => void; started: Promise<void> } {
      let release = (): void => {};
      let markStarted = (): void => {};
      const started = new Promise<void>((resolve) => {
        markStarted = resolve;
      });
      runTaskMock.mockImplementationOnce(async () => new Promise((resolve) => {
        release = (): void => resolve(ok(priceResponse(asset)));
        markStarted();
      }));
      return { release: () => release(), started };
    }

    function queried(asset: string): boolean {
      return vi.mocked(usePriceApi().queryPrices).mock.calls.some(([assets]) => assets.includes(asset));
    }

    beforeEach(() => {
      runTaskMock.mockImplementation(async () => ok(priceResponse('ANY')));
    });

    it('should run one refresh at a time, a second one waiting for the first', async () => {
      const held = holdNextTask('LANE_A');
      const first = priceTaskManager.refreshLatestPrices({ ignoreCache: false, selectedAssets: ['LANE_A'] }, vi.fn());
      const second = priceTaskManager.refreshLatestPrices({ ignoreCache: false, selectedAssets: ['LANE_B'] }, vi.fn());

      await held.started;
      await flushPromises();
      expect(queried('LANE_A')).toBe(true);
      expect(queried('LANE_B')).toBe(false);

      held.release();
      await Promise.all([first, second]);
      expect(queried('LANE_B')).toBe(true);
    });

    it('should join a refresh of the same assets and mode rather than run it twice', async () => {
      const onFetched = vi.fn();

      await Promise.all([
        priceTaskManager.refreshLatestPrices({ ignoreCache: false, selectedAssets: ['JOIN'] }, onFetched),
        priceTaskManager.refreshLatestPrices({ ignoreCache: false, selectedAssets: ['JOIN'] }, onFetched),
      ]);

      expect(usePriceApi().queryPrices).toHaveBeenCalledOnce();
      expect(onFetched).toHaveBeenCalledOnce();
    });

    it('should not join a plain price fetch of the same assets, which would apply nothing', async () => {
      const onFetched = vi.fn();

      await Promise.all([
        priceTaskManager.fetchPrices({ ignoreCache: false, selectedAssets: ['APART'] }),
        priceTaskManager.refreshLatestPrices({ ignoreCache: false, selectedAssets: ['APART'] }, onFetched),
      ]);

      expect(usePriceApi().queryPrices).toHaveBeenCalledTimes(2);
      expect(onFetched).toHaveBeenCalledOnce();
    });

    it('should fetch the exchange rates before the prices when ignoring the cache, in the same activity', async () => {
      runTaskMock.mockResolvedValueOnce(ok({ EUR: 1.5 }));
      const onFetched = vi.fn();

      await priceTaskManager.refreshLatestPrices({ ignoreCache: true, selectedAssets: ['RATES'] }, onFetched);

      const rates = vi.mocked(usePriceApi().queryFiatExchangeRates).mock.invocationCallOrder[0];
      const prices = vi.mocked(usePriceApi().queryPrices).mock.invocationCallOrder[0];
      expect(rates).toBeLessThan(prices);
      expect(get(storeToRefs(store).exchangeRates)).toMatchObject({ EUR: bigNumberify(1.5) });
      expect(onFetched).toHaveBeenCalledOnce();
    });

    it('should not apply the prices of a refresh cancelled while it fetched them', async () => {
      const held = holdNextTask('CANCEL');
      const onFetched = vi.fn();
      const refresh = priceTaskManager.refreshLatestPrices({ ignoreCache: false, selectedAssets: ['CANCEL'] }, onFetched);
      await held.started;

      useTaskOrchestrator().cancelByPrefix(ActivityKind.PRICES, ActivityPart.LATEST);
      held.release();
      await refresh;
      await flushPromises();

      expect(onFetched).not.toHaveBeenCalled();
    });

    it('should drop a queued refresh when a logout resets the orchestrator', async () => {
      const held = holdNextTask('RESET_A');
      const first = priceTaskManager.refreshLatestPrices({ ignoreCache: false, selectedAssets: ['RESET_A'] }, vi.fn());
      const second = priceTaskManager.refreshLatestPrices({ ignoreCache: false, selectedAssets: ['RESET_B'] }, vi.fn());
      await held.started;

      useTaskOrchestrator().reset();
      held.release();
      await Promise.all([first, second]);
      await flushPromises();

      expect(queried('RESET_B')).toBe(false);
    });
  });

  describe('createOracleCache', () => {
    const payload = { fromAsset: 'ETH', purgeOld: false, source: PriceOracle.CRYPTOCOMPARE, toAsset: 'USD' };

    it('should confirm once when the backend built the cache', async () => {
      runTaskMock.mockResolvedValue(ok(true));

      const result = await priceTaskManager.createOracleCache(payload);

      expect(usePriceApi().createPriceCache).toHaveBeenCalledWith(PriceOracle.CRYPTOCOMPARE, 'ETH', 'USD', false);
      expect(result.ok).toBe(true);
      expect(notifyInfo).toHaveBeenCalledOnce();
      expect(notifyError).not.toHaveBeenCalled();
    });

    it('should hand a failure back with the backend reason, leaving the report to its dock row', async () => {
      runTaskMock.mockResolvedValue(err(TaskFailed({ message: 'Rate limited' })));

      const result = await priceTaskManager.createOracleCache(payload);

      assert(!result.ok);
      expect(result.error.message).toBe('Rate limited');
      expect(notifyError).not.toHaveBeenCalled();
      expect(notifyInfo).not.toHaveBeenCalled();
    });

    it('should stay quiet when the run was cancelled', async () => {
      runTaskMock.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));

      const result = await priceTaskManager.createOracleCache(payload);

      expect(result.ok).toBe(false);
      expect(notifyError).not.toHaveBeenCalled();
      expect(notifyInfo).not.toHaveBeenCalled();
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

      runTaskMock.mockResolvedValue(ok({ assets: mockResponse, targetAsset: 'USD' }));

      const price = await priceTaskManager.getHistoricPrice({
        fromAsset: 'DAI',
        timestamp,
        toAsset: 'USD',
      });

      expect(usePriceApi().queryHistoricalRate).toHaveBeenCalledWith('DAI', 'USD', timestamp);

      expect(price).toEqual(bigNumberify(10));
    });

    it('should return minus one on failure', async () => {
      runTaskMock.mockResolvedValue(ok({ assets: {}, targetAsset: 'USD' }));

      const price = await priceTaskManager.getHistoricPrice({
        fromAsset: 'DAI',
        timestamp,
        toAsset: 'USD',
      });

      expect(price).toEqual(bigNumberify(-1));
    });

    /**
     * Two identical lookups legitimately share one activity, so the second caller's `run` never
     * executes and must still be handed the real price rather than the producer's closure local.
     */
    it('should give both concurrent callers of an identical lookup the real price', async () => {
      runTaskMock.mockResolvedValue(ok({ assets: { DAI: { [timestamp]: '10' } }, targetAsset: 'USD' }));

      const payload = { fromAsset: 'DAI', timestamp, toAsset: 'USD' };
      const [first, second] = await Promise.all([
        priceTaskManager.getHistoricPrice(payload),
        priceTaskManager.getHistoricPrice(payload),
      ]);

      expect(first).toEqual(bigNumberify(10));
      expect(second).toEqual(bigNumberify(10));
      // Genuinely deduped: the shared id means the backend was queried once, not twice.
      expect(usePriceApi().queryHistoricalRate).toHaveBeenCalledOnce();
    });

    it('should not dedup two lookups that differ only by timestamp', async () => {
      runTaskMock.mockResolvedValue(ok({ assets: { DAI: { [timestamp]: '10' } }, targetAsset: 'USD' }));

      await Promise.all([
        priceTaskManager.getHistoricPrice({ fromAsset: 'DAI', timestamp, toAsset: 'USD' }),
        priceTaskManager.getHistoricPrice({ fromAsset: 'DAI', timestamp: timestamp + 86_400_000, toAsset: 'USD' }),
      ]);

      expect(usePriceApi().queryHistoricalRate).toHaveBeenCalledTimes(2);
    });
  });
});
