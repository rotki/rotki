import type { MaybeRefOrGetter, Ref } from 'vue';
import { startPromise } from '@shared/utils';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { delay } from '@/modules/core/common/async/async-utilities';
import { onSessionCleared } from '@/modules/core/session/session-lifecycle';
import { useSetting } from '@/modules/settings/use-setting';
import { nextPacing } from '@/modules/statistics/pricing/backfill-pacing';
import { type BackfillAsset, type BackfillRequest, dayStart, planBackfill } from '@/modules/statistics/pricing/backfill-plan';
import { useBackfillRequests } from '@/modules/statistics/pricing/use-backfill-requests';
import { usePriceSeriesStore } from '@/modules/statistics/pricing/use-price-series-store';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

/** What needs pricing: an asset at a set of times, in the main currency. */
export interface BackfillDemand {
  readonly asset: string;
  /** Unix seconds. */
  readonly times: readonly number[];
}

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
  /** An oracle rate limited the last request, so the next one waits longer. */
  readonly rateLimited: Readonly<Ref<boolean>>;
}

function requestKey(request: BackfillRequest): string {
  return `${request.asset}:${request.fromTimestamp}:${request.toTimestamp}`;
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
 * Prices it gets go to the price series store, so every series of the asset sharpens. Days the
 * backend has no price for join `failedDailyPrices` and are not asked again this session.
 */
export const usePriceBackfill = createSharedComposable((): UsePriceBackfillReturn => {
  const currencySymbol = useSetting('currencySymbol');
  const { prices } = storeToRefs(usePriceSeriesStore());
  const { failedDailyPrices } = useHistoricPriceCache();
  const { cancelAll, runRequest } = useBackfillRequests();
  const { useIsActivePrefix } = useTaskCenter();
  const focused = useWindowFocus();

  const demands = shallowRef<ReadonlyMap<string, MaybeRefOrGetter<BackfillDemand | undefined>>>(new Map());
  const rateLimited = shallowRef<boolean>(false);
  const attempted = new Set<string>();
  let running = false;
  let generation = 0;
  let backoff = 0;

  const syncing = useIsActivePrefix(ActivityKind.HISTORY_SYNC);
  const fetchingDaily = useIsActivePrefix(ActivityKind.PRICES, ActivityPart.DAILY);
  const demandValues = computed<(BackfillDemand | undefined)[]>(() => Array.from(get(demands).values(), demand => toValue(demand)));
  const canRun = computed<boolean>(() =>
    get(demandValues).some(isDefined) && get(focused) && !get(syncing) && !get(fetchingDaily));

  /** The demanded assets, leaving out the main currency itself, with what is cached and known missing. */
  function backfillAssets(): BackfillAsset[] {
    const currency = get(currencySymbol);
    const timesByAsset = new Map<string, Set<number>>();
    for (const demand of get(demandValues)) {
      if (!demand || demand.asset === currency)
        continue;
      const times = timesByAsset.get(demand.asset) ?? new Set<number>();
      for (const time of demand.times)
        times.add(time);
      timesByAsset.set(demand.asset, times);
    }
    const failed = get(failedDailyPrices);
    return Array.from(timesByAsset, ([asset, times]) => ({
      asset,
      failed: new Set((failed[asset]?.noPricesTimestamps ?? []).map(dayStart)),
      known: get(prices)[asset] ?? [],
      times: [...times],
    }));
  }

  function nextRequest(): BackfillRequest | undefined {
    return planBackfill(backfillAssets()).find(request => !attempted.has(requestKey(request)));
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
      if (!isCurrent(run))
        return;
      if (result === 'rate-limited' || result === 'cancelled')
        attempted.delete(key);
      const pacing = nextPacing(result === 'rate-limited', backoff);
      backoff = pacing.backoff;
      set(rateLimited, result === 'rate-limited');
      await delay(pacing.delay);
    }
    if (isCurrent(run)) {
      running = false;
      set(rateLimited, false);
    }
  }

  function wake(): void {
    if (running || !get(canRun))
      return;
    running = true;
    startPromise(loop(++generation));
  }

  /**
   * Starts over for a new main currency or session: the tried requests and the backoff belong to
   * the old one, and a request still in flight would answer in the old currency.
   */
  function reset(): void {
    generation += 1;
    running = false;
    set(rateLimited, false);
    cancelAll();
    attempted.clear();
    backoff = 0;
  }

  function register(id: string, demand: MaybeRefOrGetter<BackfillDemand | undefined>): void {
    set(demands, new Map([...get(demands), [id, demand]]));
    tryOnScopeDispose(() => {
      const next = new Map(get(demands));
      next.delete(id);
      set(demands, next);
    });
  }

  watch(currencySymbol, () => {
    reset();
    wake();
  });
  onSessionCleared('price-backfill', reset);
  watch([canRun, demandValues], wake);

  return {
    rateLimited: readonly(rateLimited),
    register,
  };
});
