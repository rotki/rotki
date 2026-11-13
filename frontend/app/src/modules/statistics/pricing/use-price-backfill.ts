import type { MaybeRefOrGetter, Ref } from 'vue';
import { HistoricalAssetPriceResponse } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { map as mapResult } from 'plainfp/result';
import { msg } from '@/message-key';
import { priceBackfillActivity } from '@/modules/assets/prices/prices.activity';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { logger } from '@/modules/core/common/logging/logging';
import { useSetting } from '@/modules/settings/use-setting';
import { useStatisticsApi } from '@/modules/statistics/api/use-statistics-api';
import { nextPacing } from '@/modules/statistics/pricing/backfill-pacing';
import { type BackfillAsset, type BackfillRequest, planBackfill } from '@/modules/statistics/pricing/backfill-plan';
import { knownPrices } from '@/modules/statistics/pricing/price-series';
import { PricePair, usePriceSeriesStore } from '@/modules/statistics/pricing/use-price-series-store';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

/** What needs pricing: an asset at a set of times, in the main currency. */
export interface BackfillDemand {
  readonly asset: string;
  /** Unix seconds. */
  readonly times: readonly number[];
}

type RequestResult = 'ok' | 'rate-limited';

interface UsePriceBackfillReturn {
  /**
   * Adds a demand for as long as the calling scope lives.
   *
   * @remarks
   * Every demand is fetched in the background without asking, so a demand must reveal nothing
   * about holdings. Today that is the USD rate of the main currency, which rotki already asks for
   * when it loads today's exchange rates. Fetching the prices of held assets needs the user's
   * consent and is not wired here.
   */
  readonly register: (id: string, demand: MaybeRefOrGetter<BackfillDemand | undefined>) => void;
  /** Stops the current run; it resumes when its conditions next change. */
  readonly stop: () => void;
  readonly running: Readonly<Ref<boolean>>;
  /** The last request hit a rate limit, so the next one waits longer. */
  readonly rateLimited: Readonly<Ref<boolean>>;
}

function requestKey(request: BackfillRequest): string {
  return `${request.asset}:${request.fromTimestamp}:${request.toTimestamp}:${request.interval}`;
}

async function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Fetches missing historic rates from the oracles in the background, one small request at a time.
 *
 * @remarks
 * One queue serves every registered demand. Each step asks {@link planBackfill} for the next few
 * days still open and waits between requests: {@link nextPacing} sets the pace and backs off on
 * rate limits. It pauses while the window is in the background or a sync or a daily price fetch
 * runs.
 *
 * Prices it gets go to the price series store, so every series of the asset sharpens. Times the
 * backend has no price for join `failedDailyPrices` and are not asked again this session.
 */
export const usePriceBackfill = createSharedComposable((): UsePriceBackfillReturn => {
  const { t } = useI18n({ useScope: 'global' });
  const currencySymbol = useSetting('currencySymbol');
  const store = usePriceSeriesStore();
  const { mainPrices, usdPrices } = storeToRefs(store);
  const { failedDailyPrices } = useHistoricPriceCache();
  const { queryHistoricalAssetPrices } = useStatisticsApi();
  const { cancelByPrefix, submitTask } = useNativeTask();
  const { useIsActivePrefix } = useTaskCenter();
  const { getAssetField } = useAssetInfoRetrieval();
  const focused = useWindowFocus();

  const demands = shallowRef<ReadonlyMap<string, MaybeRefOrGetter<BackfillDemand | undefined>>>(new Map());
  const running = shallowRef<boolean>(false);
  const rateLimited = shallowRef<boolean>(false);
  const attempted = new Set<string>();
  let generation = 0;
  let backoff = 0;

  const syncing = useIsActivePrefix(ActivityKind.HISTORY_SYNC);
  const fetchingDaily = useIsActivePrefix(ActivityKind.PRICES, ActivityPart.DAILY);
  const demandValues = computed<(BackfillDemand | undefined)[]>(() => Array.from(get(demands).values(), demand => toValue(demand)));
  const canRun = computed<boolean>(() =>
    get(demandValues).some(isDefined) && get(focused) && !get(syncing) && !get(fetchingDaily));

  /** The demands' assets with what is cached and known missing, leaving out the main currency. */
  function backfillAssets(): BackfillAsset[] {
    const failed = get(failedDailyPrices);
    const currency = get(currencySymbol);
    const usdToMain = get(mainPrices).USD;
    return get(demandValues).flatMap(demand => (demand && demand.asset !== currency ? [demand] : [])).map(({ asset, times }) => ({
      asset,
      failed: failed[asset]?.noPricesTimestamps ?? [],
      known: knownPrices({ direct: get(mainPrices)[asset] ?? [], usdToMain, viaUsd: get(usdPrices)[asset] }),
      times,
    }));
  }

  function nextRequest(): BackfillRequest | undefined {
    return planBackfill(backfillAssets()).find(request => !attempted.has(requestKey(request)));
  }

  function recordFailures(asset: string, response: HistoricalAssetPriceResponse): void {
    if (response.noPricesTimestamps.length === 0)
      return;
    const current = get(failedDailyPrices);
    const previous = current[asset];
    set(failedDailyPrices, {
      ...current,
      [asset]: {
        noPricesTimestamps: [...new Set([...(previous?.noPricesTimestamps ?? []), ...response.noPricesTimestamps])],
        rateLimitedPricesTimestamps: response.rateLimitedPricesTimestamps,
      },
    });
  }

  async function runRequest(request: BackfillRequest): Promise<RequestResult> {
    const subject = {
      asset: request.asset,
      fromTimestamp: request.fromTimestamp,
      interval: request.interval,
      toTimestamp: request.toTimestamp,
    };
    const outcome = await submitTask<HistoricalAssetPriceResponse>({
      id: priceBackfillActivity.id(subject),
      kind: priceBackfillActivity.kind,
      run: async ({ runTask }) => mapResult(
        await runTask<HistoricalAssetPriceResponse>(async () => queryHistoricalAssetPrices({
          ...subject,
          excludeTimestamps: request.excludeTimestamps,
        })),
        result => HistoricalAssetPriceResponse.parse(result),
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.prices.backfill'), { asset: getAssetField(request.asset, 'name') }),
      title: t('task_center.group.prices'),
    });

    if (!outcome.ok) {
      logger.error(outcome.error.message);
      return 'rate-limited';
    }
    const response = outcome.value;
    store.addPrices(PricePair.MAIN, request.asset, Object.entries(response.prices)
      .filter(([, price]) => price.gt(0))
      .map(([time, price]) => ({ price, time: Number(time) })));
    recordFailures(request.asset, response);
    return response.rateLimitedPricesTimestamps.length > 0 ? 'rate-limited' : 'ok';
  }

  /** Whether `run` is still the live loop; `stop` retires older ones. */
  function isCurrent(run: number): boolean {
    return run === generation;
  }

  async function loop(run: number): Promise<void> {
    while (isCurrent(run)) {
      const request = get(canRun) ? nextRequest() : undefined;
      if (!request)
        break;
      const key = requestKey(request);
      attempted.add(key);
      const result = await runRequest(request);
      if (result === 'rate-limited')
        attempted.delete(key);
      const pacing = nextPacing(result === 'rate-limited', backoff);
      backoff = pacing.backoff;
      set(rateLimited, backoff > 0);
      await sleep(pacing.delay);
    }
    if (isCurrent(run))
      set(running, false);
  }

  function wake(): void {
    if (get(running) || !get(canRun))
      return;
    set(running, true);
    startPromise(loop(++generation));
  }

  function stop(): void {
    generation += 1;
    set(running, false);
    cancelByPrefix(priceBackfillActivity.kind, ...priceBackfillActivity.partsWithin([]));
  }

  function register(id: string, demand: MaybeRefOrGetter<BackfillDemand | undefined>): void {
    set(demands, new Map([...get(demands), [id, demand]]));
    tryOnScopeDispose(() => {
      const next = new Map(get(demands));
      next.delete(id);
      set(demands, next);
    });
  }

  watch([canRun, demandValues], wake);

  return {
    rateLimited: readonly(rateLimited),
    register,
    running: readonly(running),
    stop,
  };
});
