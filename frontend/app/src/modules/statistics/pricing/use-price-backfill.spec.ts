import type { FailedHistoricalAssetPriceResponse, HistoricalAssetPricePayload } from '@rotki/common';
import type { ComputedRef } from 'vue';
import { createCustomPinia } from '@test/utils/create-pinia';
import { withSetup } from '@test/utils/with-setup';
import { get, set } from '@vueuse/shared';
import { setActivePinia } from 'pinia';
import { err, ok } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { SECONDS_PER_DAY } from '@/modules/core/common/constraints';
import { defaultGeneralSettings } from '@/modules/settings/factories';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { BACKOFF_START_MS, REQUEST_DELAY_MS } from '@/modules/statistics/pricing/backfill-pacing';
import { type BackfillDemand, usePriceBackfill } from '@/modules/statistics/pricing/use-price-backfill';
import { usePriceSeriesStore } from '@/modules/statistics/pricing/use-price-series-store';

/** The response as the backend sends it, before parsing, or `fail` for a request that fails outright. */
type RawPriceResponse = {
  /** Left out as an older backend does, which parses as none. */
  failedPricesTimestamps?: number[];
  noPricesTimestamps: number[];
  prices: Record<string, string>;
  rateLimitedPricesTimestamps: number[];
} | 'fail' | 'fail-network' | 'no-response' | 'malformed' | 'cancel';

const { cancelByPrefix, failedDailyPrices, focused, queryHistoricalAssetPrices, responder, responses } = await vi.hoisted(async () => {
  const { ref, shallowRef } = await import('vue');
  const pending: RawPriceResponse[] = [];
  /** Answers a request by what it asks for, ahead of the queued responses; unset by default. */
  const answers: { answer?: (payload: HistoricalAssetPricePayload) => RawPriceResponse | undefined } = {};
  return {
    responder: answers,
    cancelByPrefix: vi.fn(),
    failedDailyPrices: shallowRef<Record<string, FailedHistoricalAssetPriceResponse>>({}),
    focused: ref<boolean>(true),
    queryHistoricalAssetPrices: vi.fn<(payload: HistoricalAssetPricePayload) => Promise<{ taskId: number }>>(async () => ({ taskId: 1 })),
    responses: pending,
  };
});

vi.mock('@vueuse/core', async (importOriginal): Promise<typeof import('@vueuse/core')> => ({
  ...await importOriginal<typeof import('@vueuse/core')>(),
  useWindowFocus: (): typeof focused => focused,
}));

vi.mock('@/modules/statistics/api/use-statistics-api', () => ({
  useStatisticsApi: (): { queryHistoricalAssetPrices: typeof queryHistoricalAssetPrices } => ({ queryHistoricalAssetPrices }),
}));

vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: (): { failedDailyPrices: typeof failedDailyPrices } => ({ failedDailyPrices }),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): { getAssetField: (asset: string) => string } => ({ getAssetField: (asset: string): string => asset }),
}));

vi.mock('@/modules/task-center/use-task-center', async (): Promise<unknown> => {
  const { computed } = await import('vue');
  return {
    useTaskCenter: (): { useIsActivePrefix: () => ComputedRef<boolean> } => ({ useIsActivePrefix: (): ComputedRef<boolean> => computed<boolean>(() => false) }),
  };
});

vi.mock('@/modules/task-center/use-native-task', async (): Promise<unknown> => {
  const { Cancelled, TaskFailed } = await import('@/modules/core/tasks/task-result');
  const { ApiRequestError } = await import('@/modules/core/api/types/errors');
  const { FetchError } = await import('ofetch');
  const outcomes: Record<Extract<RawPriceResponse, string>, () => unknown> = {
    'cancel': () => err(Cancelled({ message: 'cancelled from the task center' })),
    'fail': () => err(TaskFailed({ message: 'the backend rejected the request' })),
    // as the task layer hands over a 502 outcome
    'fail-network': () => err(TaskFailed({ cause: new ApiRequestError('the price sources could not be reached', { failureCause: 'network', status: 502 }), message: 'the price sources could not be reached' })),
    'malformed': () => ok({ prices: 'not a price map' }),
    // the request never got an answer, so no backend named a cause
    'no-response': () => err(TaskFailed({ cause: new FetchError('[POST] "/api/1/balances/historical/asset/prices": <no response> fetch failed'), message: 'fetch failed' })),
  };
  return {
    useNativeTask: (): { cancelByPrefix: typeof cancelByPrefix; submitTask: (spec: { run: (ctx: unknown) => Promise<unknown> }) => Promise<unknown> } => ({
      cancelByPrefix,
      submitTask: async (spec: { run: (ctx: unknown) => Promise<unknown> }): Promise<unknown> => spec.run({
        cancelled: (): boolean => false,
        report: vi.fn(),
        rerun: false,
        runTask: async (task: () => Promise<unknown>): Promise<unknown> => {
          await task();
          const payload = queryHistoricalAssetPrices.mock.lastCall?.[0];
          const answered = payload ? responder.answer?.(payload) : undefined;
          const next = answered ?? responses.shift() ?? { noPricesTimestamps: [], prices: {}, rateLimitedPricesTimestamps: [] };
          return typeof next === 'string' ? outcomes[next]() : ok(next);
        },
      }),
    }),
  };
});

const days = [0, 1, 2, 3].map(day => day * SECONDS_PER_DAY);

function flatPrices(times: number[], price = '10'): Record<string, string> {
  return Object.fromEntries(times.map(time => [time.toString(), price]));
}

function demand(): BackfillDemand {
  return { asset: 'BTC', times: days.map(day => day + SECONDS_PER_DAY / 2) };
}

describe('modules/statistics/pricing/use-price-backfill', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setActivePinia(createCustomPinia());
    set(focused, true);
    set(failedDailyPrices, {});
    responses.length = 0;
    responder.answer = undefined;
    queryHistoricalAssetPrices.mockClear();
    cancelByPrefix.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should fetch nothing while nothing is registered', async () => {
    withSetup(() => usePriceBackfill());
    await vi.advanceTimersByTimeAsync(REQUEST_DELAY_MS * 3);
    expect(queryHistoricalAssetPrices).not.toHaveBeenCalled();
  });

  it('should start with a coarse rate, store the prices and stop once settled', async () => {
    responses.push({ noPricesTimestamps: [], prices: flatPrices(days), rateLimitedPricesTimestamps: [] });
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(REQUEST_DELAY_MS * 5);

    expect(queryHistoricalAssetPrices).toHaveBeenCalledOnce();
    expect(queryHistoricalAssetPrices).toHaveBeenCalledWith(expect.objectContaining({
      asset: 'BTC',
      excludeTimestamps: [SECONDS_PER_DAY],
      fromTimestamp: 0,
      interval: SECONDS_PER_DAY,
      toTimestamp: SECONDS_PER_DAY,
    }));
    expect(usePriceSeriesStore().prices.BTC).toHaveLength(days.length);
  });

  it('should remember days with no price and not ask for them again', async () => {
    const failed = days[2];
    responses.push({ noPricesTimestamps: [failed], prices: flatPrices(days.filter(day => day !== failed)), rateLimitedPricesTimestamps: [] });
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(REQUEST_DELAY_MS * 5);

    expect(get(failedDailyPrices).BTC?.noPricesTimestamps).toEqual([failed]);
    expect(queryHistoricalAssetPrices).toHaveBeenCalledOnce();
  });

  it('should back off after a rate limit before asking again, and say so', async () => {
    responses.push({ noPricesTimestamps: [], prices: {}, rateLimitedPricesTimestamps: days });
    const { result } = withSetup(() => {
      const backfill = usePriceBackfill();
      backfill.register('rates', demand());
      return backfill;
    });
    await vi.advanceTimersByTimeAsync(BACKOFF_START_MS - 1);
    expect(queryHistoricalAssetPrices).toHaveBeenCalledOnce();
    expect(get(result.rateLimited)).toBe(true);

    await vi.advanceTimersByTimeAsync(1);
    expect(queryHistoricalAssetPrices).toHaveBeenCalledTimes(2);
  });

  it('should ask again for a day an oracle could not reach, after a backoff and without calling it a rate limit', async () => {
    responses.push({ failedPricesTimestamps: [days[0]], noPricesTimestamps: [], prices: {}, rateLimitedPricesTimestamps: [] });
    const askedForTheDay = (): number => queryHistoricalAssetPrices.mock.calls.filter(([payload]) => payload.fromTimestamp === days[0]).length;
    const { result } = withSetup(() => {
      const backfill = usePriceBackfill();
      backfill.register('rates', demand());
      return backfill;
    });
    await vi.advanceTimersByTimeAsync(BACKOFF_START_MS - 1);
    expect(askedForTheDay()).toBe(1);
    expect(get(result.rateLimited)).toBe(false);

    await vi.advanceTimersByTimeAsync(1);
    expect(askedForTheDay()).toBe(2);
    expect(get(failedDailyPrices).BTC).toBeUndefined();
  });

  it('should go on with other days while an unreachable day waits for its retry', async () => {
    responses.push({ failedPricesTimestamps: [days[0]], noPricesTimestamps: [], prices: {}, rateLimitedPricesTimestamps: [] });
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(REQUEST_DELAY_MS);

    expect(queryHistoricalAssetPrices).toHaveBeenCalledTimes(2);
    expect(queryHistoricalAssetPrices).toHaveBeenLastCalledWith(expect.not.objectContaining({ fromTimestamp: days[0] }));
  });

  it('should ask for a newly registered asset at once while another asset\'s day waits for its retry', async () => {
    responder.answer = (payload): RawPriceResponse | undefined => payload.asset === 'BTC' && payload.fromTimestamp === days[0]
      ? { failedPricesTimestamps: [days[0]], noPricesTimestamps: [], prices: {}, rateLimitedPricesTimestamps: [] }
      : undefined;
    const { result } = withSetup(() => {
      const backfill = usePriceBackfill();
      backfill.register('rates', demand());
      return backfill;
    });
    // the other BTC days are settled and day 0 waits for its retry, a minute after its first ask
    await vi.advanceTimersByTimeAsync(REQUEST_DELAY_MS * 2);
    const before = queryHistoricalAssetPrices.mock.calls.length;

    withSetup(() => result.register('eth', { asset: 'ETH', times: [SECONDS_PER_DAY / 2] }));
    await vi.advanceTimersByTimeAsync(0);
    expect(queryHistoricalAssetPrices.mock.calls.slice(before)).toEqual([[expect.objectContaining({ asset: 'ETH' })]]);
  });

  it('should still give up on a day that alternates between unreachable and rate limited', async () => {
    const { findCurrency } = useCurrencies();
    const usd = findCurrency('USD');
    useSettingsRepo().updateGeneral({ ...defaultGeneralSettings(usd), mainCurrency: usd, oraclePenaltyDuration: 600 });
    let asks = 0;
    responder.answer = (payload): RawPriceResponse | undefined => {
      if (payload.fromTimestamp !== days[0])
        return undefined;
      asks += 1;
      return asks % 2 === 0
        ? { failedPricesTimestamps: [], noPricesTimestamps: [], prices: {}, rateLimitedPricesTimestamps: [days[0]] }
        : { failedPricesTimestamps: [days[0]], noPricesTimestamps: [], prices: {}, rateLimitedPricesTimestamps: [] };
    };
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(2 * 60 * 60 * 1000);

    expect(get(failedDailyPrices).BTC?.failedPricesTimestamps).toEqual([days[0]]);
  });

  it('should move a day a daily fetch could not fetch to the missing prices once it reports no price', async () => {
    set(failedDailyPrices, { BTC: { failedPricesTimestamps: [days[0]], noPricesTimestamps: [], rateLimitedPricesTimestamps: [days[0]] } });
    responses.push({ noPricesTimestamps: [days[0]], prices: {}, rateLimitedPricesTimestamps: [] });
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(REQUEST_DELAY_MS);

    expect(get(failedDailyPrices).BTC).toEqual({ failedPricesTimestamps: [], noPricesTimestamps: [days[0]], rateLimitedPricesTimestamps: [] });
  });

  it('should take a day it priced off the lists of a daily fetch that could not price it', async () => {
    set(failedDailyPrices, { BTC: { failedPricesTimestamps: [days[0]], noPricesTimestamps: [], rateLimitedPricesTimestamps: [days[0]] } });
    responses.push({ noPricesTimestamps: [], prices: flatPrices(days), rateLimitedPricesTimestamps: [] });
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(REQUEST_DELAY_MS);

    expect(usePriceSeriesStore().prices.BTC).toHaveLength(days.length);
    expect(get(failedDailyPrices).BTC).toBeUndefined();
  });

  it('should still give up on an unreachable day whose retry fails outright, instead of leaving it pending', async () => {
    const { findCurrency } = useCurrencies();
    const usd = findCurrency('USD');
    useSettingsRepo().updateGeneral({ ...defaultGeneralSettings(usd), mainCurrency: usd, oraclePenaltyDuration: 600 });
    let asks = 0;
    responder.answer = (payload): RawPriceResponse | undefined => {
      if (payload.fromTimestamp !== days[0])
        return undefined;
      asks += 1;
      return asks === 1
        ? { failedPricesTimestamps: [days[0]], noPricesTimestamps: [], prices: {}, rateLimitedPricesTimestamps: [] }
        : 'fail';
    };
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(2 * 60 * 60 * 1000);

    expect(asks).toBeGreaterThan(2);
    expect(get(failedDailyPrices).BTC?.failedPricesTimestamps).toEqual([days[0]]);
  });

  it('should ask again for the days of a request that failed on the network, as unreachable ones', async () => {
    responder.answer = (payload): RawPriceResponse | undefined => {
      if (payload.fromTimestamp !== days[0])
        return undefined;
      const asks = queryHistoricalAssetPrices.mock.calls.filter(([call]) => call.fromTimestamp === days[0]).length;
      return asks === 1 ? 'fail-network' : { noPricesTimestamps: [], prices: flatPrices([days[0]]), rateLimitedPricesTimestamps: [] };
    };
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(BACKOFF_START_MS);

    const askedForTheDay = queryHistoricalAssetPrices.mock.calls.filter(([payload]) => payload.fromTimestamp === days[0]);
    expect(askedForTheDay).toHaveLength(2);
    expect(usePriceSeriesStore().prices.BTC?.some(({ time }) => time === days[0])).toBe(true);
    expect(get(failedDailyPrices).BTC).toBeUndefined();
  });

  it('should ask again for the days of a request that got no response, as unreachable ones', async () => {
    responder.answer = (payload): RawPriceResponse | undefined => {
      if (payload.fromTimestamp !== days[0])
        return undefined;
      const asks = queryHistoricalAssetPrices.mock.calls.filter(([call]) => call.fromTimestamp === days[0]).length;
      return asks === 1 ? 'no-response' : { noPricesTimestamps: [], prices: flatPrices([days[0]]), rateLimitedPricesTimestamps: [] };
    };
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(BACKOFF_START_MS);

    const askedForTheDay = queryHistoricalAssetPrices.mock.calls.filter(([payload]) => payload.fromTimestamp === days[0]);
    expect(askedForTheDay).toHaveLength(2);
    expect(usePriceSeriesStore().prices.BTC?.some(({ time }) => time === days[0])).toBe(true);
  });

  it('should ask for an unreachable day once more after the penalty is over before giving up on it', async () => {
    const { findCurrency } = useCurrencies();
    const usd = findCurrency('USD');
    useSettingsRepo().updateGeneral({ ...defaultGeneralSettings(usd), mainCurrency: usd, oraclePenaltyDuration: 1800 });
    let firstAsk: number | undefined;
    // the penalty started just after the day's first unreachable answer and still applies at its last second
    responder.answer = (payload): RawPriceResponse | undefined => {
      if (payload.fromTimestamp !== days[0])
        return undefined;
      firstAsk ??= Date.now();
      return Date.now() - firstAsk <= (1800 + 30) * 1000
        ? { failedPricesTimestamps: [days[0]], noPricesTimestamps: [], prices: {}, rateLimitedPricesTimestamps: [] }
        : { noPricesTimestamps: [], prices: flatPrices([days[0]]), rateLimitedPricesTimestamps: [] };
    };
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(60 * 60 * 1000);

    expect(usePriceSeriesStore().prices.BTC?.some(({ time }) => time === days[0])).toBe(true);
    expect(get(failedDailyPrices).BTC).toBeUndefined();
  });

  it('should wait out a penalty that began only after the threshold of failures before giving up on a day', async () => {
    const { findCurrency } = useCurrencies();
    const usd = findCurrency('USD');
    useSettingsRepo().updateGeneral({ ...defaultGeneralSettings(usd), mainCurrency: usd, oraclePenaltyDuration: 1800, oraclePenaltyThresholdCount: 5 });
    let failures = 0;
    let penalizedAt: number | undefined;
    // the oracle fails five times, its sixth failure penalizes it for 1800s, and it answers after that
    responder.answer = (payload): RawPriceResponse | undefined => {
      if (payload.fromTimestamp !== days[0])
        return undefined;
      if (penalizedAt !== undefined && Date.now() - penalizedAt > 1800 * 1000)
        return { noPricesTimestamps: [], prices: flatPrices([days[0]]), rateLimitedPricesTimestamps: [] };
      failures += 1;
      if (failures === 6)
        penalizedAt = Date.now();
      return { failedPricesTimestamps: [days[0]], noPricesTimestamps: [], prices: {}, rateLimitedPricesTimestamps: [] };
    };
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(2 * 60 * 60 * 1000);

    expect(usePriceSeriesStore().prices.BTC?.some(({ time }) => time === days[0])).toBe(true);
    expect(get(failedDailyPrices).BTC).toBeUndefined();
  });

  it('should keep the failed and rate-limited days the daily price fetcher reported when it files a missing day', async () => {
    const fetched = { failedPricesTimestamps: [999 * SECONDS_PER_DAY], noPricesTimestamps: [], rateLimitedPricesTimestamps: [888 * SECONDS_PER_DAY] };
    set(failedDailyPrices, { BTC: fetched });
    responses.push({ failedPricesTimestamps: [days[1]], noPricesTimestamps: [days[0]], prices: {}, rateLimitedPricesTimestamps: [] });
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(REQUEST_DELAY_MS);

    expect(get(failedDailyPrices).BTC).toEqual({ ...fetched, noPricesTimestamps: [days[0]] });
  });

  it('should keep asking for an unreachable day through an oracle penalty, then leave it to the user without calling it priceless', async () => {
    const { findCurrency } = useCurrencies();
    const usd = findCurrency('USD');
    useSettingsRepo().updateGeneral({ ...defaultGeneralSettings(usd), mainCurrency: usd, oraclePenaltyDuration: 600 });
    // asked at 0s, 60s, 180s, 420s, 900s and 1800s, the sixth one surely penalized, then at 2700s, past its penalty
    const asks = 7;
    responder.answer = (payload): RawPriceResponse | undefined => payload.fromTimestamp === days[0]
      ? { failedPricesTimestamps: [days[0]], noPricesTimestamps: [], prices: {}, rateLimitedPricesTimestamps: [] }
      : undefined;
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(60 * 60 * 1000);

    const askedForTheDay = queryHistoricalAssetPrices.mock.calls.filter(([payload]) => payload.fromTimestamp === days[0]);
    expect(askedForTheDay).toHaveLength(asks);
    expect(get(failedDailyPrices).BTC?.failedPricesTimestamps).toEqual([days[0]]);
    expect(get(failedDailyPrices).BTC?.noPricesTimestamps).toEqual([]);
  });

  it('should back off after a failed request and move on, without calling its days priceless', async () => {
    responses.push('fail');
    const { result } = withSetup(() => {
      const backfill = usePriceBackfill();
      backfill.register('rates', demand());
      return backfill;
    });
    await vi.advanceTimersByTimeAsync(BACKOFF_START_MS - 1);
    expect(queryHistoricalAssetPrices).toHaveBeenCalledOnce();

    await vi.advanceTimersByTimeAsync(1);
    expect(queryHistoricalAssetPrices).toHaveBeenCalledTimes(2);
    expect(queryHistoricalAssetPrices).toHaveBeenLastCalledWith(expect.objectContaining({ fromTimestamp: days[1], toTimestamp: days[3] }));
    expect(get(failedDailyPrices).BTC).toBeUndefined();
    expect(get(result.rateLimited)).toBe(false);
  });

  it('should move on past a malformed response rather than blame the oracles or stall', async () => {
    responses.push('malformed');
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(REQUEST_DELAY_MS * 5);

    expect(get(failedDailyPrices).BTC).toBeUndefined();
    expect(queryHistoricalAssetPrices).toHaveBeenCalledTimes(2);
    expect(queryHistoricalAssetPrices).toHaveBeenLastCalledWith(expect.objectContaining({ fromTimestamp: days[1], toTimestamp: days[3] }));
  });

  it('should stop for the session once the user cancels one of its activities', async () => {
    responses.push('cancel');
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(REQUEST_DELAY_MS * 5);

    expect(queryHistoricalAssetPrices).toHaveBeenCalledOnce();
  });

  it('should start over in a new main currency instead of skipping days it tried in the old one', async () => {
    responses.push({ noPricesTimestamps: [], prices: flatPrices(days), rateLimitedPricesTimestamps: [] });
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(REQUEST_DELAY_MS);
    expect(queryHistoricalAssetPrices).toHaveBeenCalledOnce();

    const { findCurrency } = useCurrencies();
    useSettingsRepo().updateGeneral({ ...defaultGeneralSettings(findCurrency('EUR')), mainCurrency: findCurrency('EUR') });
    await vi.advanceTimersByTimeAsync(0);

    expect(queryHistoricalAssetPrices).toHaveBeenCalledTimes(2);
    expect(cancelByPrefix).toHaveBeenCalledWith('prices', 'backfill');
  });

  it('should pause while the window is unfocused and resume when it comes back', async () => {
    set(focused, false);
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(REQUEST_DELAY_MS);
    expect(queryHistoricalAssetPrices).not.toHaveBeenCalled();

    set(focused, true);
    await vi.advanceTimersByTimeAsync(0);
    expect(queryHistoricalAssetPrices).toHaveBeenCalledOnce();
  });
});
