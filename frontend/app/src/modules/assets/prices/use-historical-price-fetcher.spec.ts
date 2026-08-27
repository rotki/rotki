import type { FailedHistoricalAssetPriceResponse, HistoricalAssetPricePayload } from '@rotki/common';
import type { ActivityContext, NativeActivitySpec } from '@/modules/task-center/use-native-task';
import { createMock } from '@test/utils/create-mock';
import { err, ok, type Result } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { BackendCancelled, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useHistoricalPriceFetcher } from './use-historical-price-fetcher';

const {
  failedDailyPrices,
  getAssetField,
  notifyError,
  queryHistoricalAssetPrices,
  resolvedFailedDailyPrices,
  runTask,
} = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    failedDailyPrices: ref<Record<string, FailedHistoricalAssetPriceResponse>>({}),
    getAssetField: vi.fn(() => 'Ethereum'),
    notifyError: vi.fn(),
    queryHistoricalAssetPrices: vi.fn(),
    resolvedFailedDailyPrices: ref<Record<string, number[]>>({}),
    runTask: vi.fn(),
  };
});

let submitted: NativeActivitySpec<unknown> | undefined;

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: (): Record<string, unknown> => ({
    submitTask: async <T>(spec: NativeActivitySpec<T>): Promise<Result<T, TaskError>> => {
      submitted = spec;
      return spec.run(createMock<ActivityContext>({ runTask }));
    },
  }),
}));

vi.mock('@/modules/statistics/api/use-statistics-api', () => ({
  useStatisticsApi: (): Record<string, unknown> => ({ queryHistoricalAssetPrices }),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): Record<string, unknown> => ({ getAssetField }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: (): Record<string, unknown> => ({ notifyError }),
}));

vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: (): Record<string, unknown> => ({ failedDailyPrices, resolvedFailedDailyPrices }),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  getDefaultLogLevel: vi.fn(() => 'debug'),
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
  setLevel: vi.fn(),
}));

const ASSET = 'ETH';

function payload(overrides: Partial<HistoricalAssetPricePayload> = {}): HistoricalAssetPricePayload {
  return {
    asset: ASSET,
    fromTimestamp: 1600000000,
    interval: 86400,
    toTimestamp: 1700000000,
    ...overrides,
  };
}

function backendReturns(response: {
  noPricesTimestamps?: number[];
  prices?: Record<string, string>;
  rateLimitedPricesTimestamps?: number[];
}): void {
  queryHistoricalAssetPrices.mockResolvedValue({
    noPricesTimestamps: [],
    prices: {},
    rateLimitedPricesTimestamps: [],
    ...response,
  });
  runTask.mockImplementation(async (run: () => Promise<unknown>) => ok(await run()));
}

describe('modules/assets/prices/useHistoricalPriceFetcher', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(failedDailyPrices, {});
    set(resolvedFailedDailyPrices, {});
    submitted = undefined;
    backendReturns({});
  });

  describe('the activity it submits', () => {
    it('should key the activity on the range as well as the asset, so two ranges cannot dedup onto one', async () => {
      const { fetchHistoricalAssetPrice } = useHistoricalPriceFetcher();

      await fetchHistoricalAssetPrice(payload());

      expect(submitted?.id).toBe(makeActivityId(
        ActivityKind.PRICES,
        ActivityPart.DAILY,
        ASSET,
        86400,
        1600000000,
        1700000000,
      ));
    });

    it('should give two ranges of one asset different ids', async () => {
      const { fetchHistoricalAssetPrice } = useHistoricalPriceFetcher();

      await fetchHistoricalAssetPrice(payload());
      const first = submitted?.id;
      await fetchHistoricalAssetPrice(payload({ toTimestamp: 1650000000 }));

      expect(submitted?.id).not.toBe(first);
    });

    it('should file the activity under prices and allow a re-run', async () => {
      const { fetchHistoricalAssetPrice } = useHistoricalPriceFetcher();

      await fetchHistoricalAssetPrice(payload());

      expect(submitted?.kind).toBe(ActivityKind.PRICES);
      expect(submitted?.rerunnable).toBe(true);
    });

    it('should name the asset in the subtitle rather than showing its identifier', async () => {
      getAssetField.mockReturnValue('Ethereum');
      const { fetchHistoricalAssetPrice } = useHistoricalPriceFetcher();

      await fetchHistoricalAssetPrice(payload());

      expect(getAssetField).toHaveBeenCalledWith(ASSET, 'name');
      expect(submitted?.subtitle).toMatchObject({ params: { asset: 'Ethereum' } });
    });
  });

  describe('the timestamps it asks the backend to skip', () => {
    it('should skip nothing on a first fetch', async () => {
      const { fetchHistoricalAssetPrice } = useHistoricalPriceFetcher();

      await fetchHistoricalAssetPrice(payload());

      expect(queryHistoricalAssetPrices).toHaveBeenCalledWith({ ...payload(), excludeTimestamps: [] });
    });

    it('should skip the timestamps already known to have no price', async () => {
      set(failedDailyPrices, {
        [ASSET]: { noPricesTimestamps: [111, 222], rateLimitedPricesTimestamps: [] },
      });
      const { fetchHistoricalAssetPrice } = useHistoricalPriceFetcher();

      await fetchHistoricalAssetPrice(payload());

      expect(queryHistoricalAssetPrices).toHaveBeenCalledWith({ ...payload(), excludeTimestamps: [111, 222] });
    });

    it('should stop skipping a timestamp the user has since resolved by hand', async () => {
      set(failedDailyPrices, {
        [ASSET]: { noPricesTimestamps: [111, 222], rateLimitedPricesTimestamps: [] },
      });
      set(resolvedFailedDailyPrices, { [ASSET]: [111] });
      const { fetchHistoricalAssetPrice } = useHistoricalPriceFetcher();

      await fetchHistoricalAssetPrice(payload());

      expect(queryHistoricalAssetPrices).toHaveBeenCalledWith({ ...payload(), excludeTimestamps: [222] });
    });

    it('should not skip another asset\'s failures', async () => {
      set(failedDailyPrices, {
        BTC: { noPricesTimestamps: [111], rateLimitedPricesTimestamps: [] },
      });
      const { fetchHistoricalAssetPrice } = useHistoricalPriceFetcher();

      await fetchHistoricalAssetPrice(payload());

      expect(queryHistoricalAssetPrices).toHaveBeenCalledWith({ ...payload(), excludeTimestamps: [] });
    });
  });

  describe('what it records after a fetch', () => {
    it('should record the timestamps the backend could not price', async () => {
      backendReturns({ noPricesTimestamps: [333] });
      const { fetchHistoricalAssetPrice } = useHistoricalPriceFetcher();

      await fetchHistoricalAssetPrice(payload());

      expect(get(failedDailyPrices)[ASSET]).toEqual({
        noPricesTimestamps: [333],
        rateLimitedPricesTimestamps: [],
      });
    });

    it('should record a rate limit separately from a missing price', async () => {
      backendReturns({ rateLimitedPricesTimestamps: [444] });
      const { fetchHistoricalAssetPrice } = useHistoricalPriceFetcher();

      await fetchHistoricalAssetPrice(payload());

      expect(get(failedDailyPrices)[ASSET]).toEqual({
        noPricesTimestamps: [],
        rateLimitedPricesTimestamps: [444],
      });
    });

    it('should keep skipping the excluded timestamps the backend was never asked about', async () => {
      set(failedDailyPrices, {
        [ASSET]: { noPricesTimestamps: [111], rateLimitedPricesTimestamps: [] },
      });
      backendReturns({});
      const { fetchHistoricalAssetPrice } = useHistoricalPriceFetcher();

      await fetchHistoricalAssetPrice(payload());

      expect(get(failedDailyPrices)[ASSET]).toEqual({
        noPricesTimestamps: [111],
        rateLimitedPricesTimestamps: [],
      });
    });

    it('should clear the asset once nothing failed and nothing was skipped', async () => {
      set(failedDailyPrices, {
        BTC: { noPricesTimestamps: [999], rateLimitedPricesTimestamps: [] },
        [ASSET]: { noPricesTimestamps: [], rateLimitedPricesTimestamps: [] },
      });
      set(resolvedFailedDailyPrices, { [ASSET]: [111] });
      const { fetchHistoricalAssetPrice } = useHistoricalPriceFetcher();

      await fetchHistoricalAssetPrice(payload());

      expect(get(failedDailyPrices)).not.toHaveProperty(ASSET);
      expect(get(resolvedFailedDailyPrices)).not.toHaveProperty(ASSET);
      expect(get(failedDailyPrices).BTC).toBeDefined();
    });
  });

  describe('the value it returns', () => {
    it('should return the parsed prices', async () => {
      backendReturns({ prices: { 1600000000: '1500.5' } });
      const { fetchHistoricalAssetPrice } = useHistoricalPriceFetcher();

      const result = await fetchHistoricalAssetPrice(payload());

      expect(result.prices[1600000000].toString()).toBe('1500.5');
    });

    it('should return an empty response when the task fails, rather than throwing', async () => {
      runTask.mockResolvedValue(err(TaskFailed({ message: 'boom' })));
      const { fetchHistoricalAssetPrice } = useHistoricalPriceFetcher();

      const result = await fetchHistoricalAssetPrice(payload());

      expect(result).toEqual({ noPricesTimestamps: [], prices: {}, rateLimitedPricesTimestamps: [] });
    });
  });

  describe('how it reports a failure', () => {
    it('should notify the user when the task actually failed', async () => {
      runTask.mockResolvedValue(err(TaskFailed({ message: 'boom' })));
      const { fetchHistoricalAssetPrice } = useHistoricalPriceFetcher();

      await fetchHistoricalAssetPrice(payload());

      expect(notifyError).toHaveBeenCalledOnce();
    });

    it('should stay quiet when the task was cancelled rather than failed', async () => {
      runTask.mockResolvedValue(err(BackendCancelled({ message: 'stopped' })));
      const { fetchHistoricalAssetPrice } = useHistoricalPriceFetcher();

      const result = await fetchHistoricalAssetPrice(payload());

      expect(notifyError).not.toHaveBeenCalled();
      expect(result).toEqual({ noPricesTimestamps: [], prices: {}, rateLimitedPricesTimestamps: [] });
    });

    it('should leave the recorded failures untouched when the task fails', async () => {
      set(failedDailyPrices, {
        [ASSET]: { noPricesTimestamps: [111], rateLimitedPricesTimestamps: [] },
      });
      runTask.mockResolvedValue(err(TaskFailed({ message: 'boom' })));
      const { fetchHistoricalAssetPrice } = useHistoricalPriceFetcher();

      await fetchHistoricalAssetPrice(payload());

      expect(get(failedDailyPrices)[ASSET]).toEqual({
        noPricesTimestamps: [111],
        rateLimitedPricesTimestamps: [],
      });
    });
  });
});
