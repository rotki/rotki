import type { MaybeRefOrGetter, Ref } from 'vue';
import type { RequestResult } from '@/modules/statistics/pricing/backfill-outcome';
import { startPromise } from '@shared/utils';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { delay } from '@/modules/core/common/async/async-utilities';
import { onSessionCleared } from '@/modules/core/session/session-lifecycle';
import { useSetting } from '@/modules/settings/use-setting';
import { nextPacing } from '@/modules/statistics/pricing/backfill-pacing';
import { type BackfillAsset, type BackfillRequest, dayStart, planBackfill, requestedDays } from '@/modules/statistics/pricing/backfill-plan';
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
  /** The days of an asset the backfill stopped asking for because they stayed unreachable. Reactive. */
  readonly givenUpDays: (asset: string) => ReadonlySet<number>;
}

/** Days whose request was rate limited, unreachable or cancelled are asked for again later. */
function isAskedAgain(result: RequestResult): boolean {
  return result === 'rate-limited' || result === 'unreachable' || result === 'cancelled';
}

/**
 * Outcomes that back the queue off before the next request. Unreachable days wait on their own,
 * so the other days go ahead at the normal pace.
 */
function isFailure(result: RequestResult): boolean {
  return result === 'rate-limited' || result === 'failed';
}

/**
 * Fetches missing historic rates from the oracles in the background, one small request at a time.
 *
 * @remarks
 * One queue serves every registered demand. Each step asks {@link planBackfill} for the next few
 * days still open and waits between requests: {@link nextPacing} sets the pace and backs off on
 * rate limits and failures. It pauses while the window is in the background or a sync or a daily
 * price fetch runs, and stops for the session when the user cancels one of its activities.
 *
 * Prices it gets go to the price series store, so every series of the asset sharpens. Days the
 * backend has no price for join `failedDailyPrices`. A day asked once is not asked again this
 * session unless an oracle rate limited it or could not be reached, so a request that settles
 * nothing cannot stall the queue on the same days. An unreachable day waits for its own retry time
 * while the queue moves on to other days, and once it stays unreachable for longer than an oracle
 * penalty the backfill no longer asks for it.
 */
export const usePriceBackfill = createSharedComposable((): UsePriceBackfillReturn => {
  const currencySymbol = useSetting('currencySymbol');
  const { prices } = storeToRefs(usePriceSeriesStore());
  const { failedDailyPrices } = useHistoricPriceCache();
  const { cancelAll, forgetAttempts, givenUpDays, isUnreachable, nextRetryAt, runRequest, waitingDays } = useBackfillRequests();
  const { useIsActivePrefix } = useTaskCenter();
  const focused = useWindowFocus();

  const demands = shallowRef<ReadonlyMap<string, MaybeRefOrGetter<BackfillDemand | undefined>>>(new Map());
  const rateLimited = shallowRef<boolean>(false);
  /** Per asset, the days asked this session that asking again would not help. */
  const tried = new Map<string, Set<number>>();
  let running = false;
  /** The user cancelled a backfill activity; it stays stopped until the currency or session changes. */
  let paused = false;
  let generation = 0;
  let backoff = 0;
  /** Wakes the queue when the next unreachable day may be asked for again. */
  let retryTimer: ReturnType<typeof setTimeout> | undefined;

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
      known: get(prices)[asset] ?? [],
      skipped: new Set([
        ...(failed[asset]?.noPricesTimestamps ?? []).map(dayStart),
        ...Array.from(givenUpDays(asset), dayStart),
        ...Array.from(waitingDays(asset), dayStart),
        ...(tried.get(asset) ?? []),
      ]),
      times: [...times],
    }));
  }

  function nextRequest(): BackfillRequest | undefined {
    return planBackfill(backfillAssets())[0];
  }

  function markTried(asset: string, days: readonly number[]): void {
    const assetDays = tried.get(asset) ?? new Set<number>();
    for (const day of days)
      assetDays.add(day);
    tried.set(asset, assetDays);
  }

  function forgetTried(asset: string, days: readonly number[]): void {
    const assetDays = tried.get(asset);
    for (const day of days)
      assetDays?.delete(day);
  }

  /** Whether `run` is still the live loop; `stop` retires older ones. */
  function isCurrent(run: number): boolean {
    return run === generation;
  }

  function clearRetry(): void {
    clearTimeout(retryTimer);
    retryTimer = undefined;
  }

  /**
   * Once the queue has nothing open but unreachable days wait, wakes it when the first may be
   * asked for again. The loop has ended by then, so new demand starts a loop at once meanwhile.
   */
  function scheduleRetry(): void {
    clearRetry();
    const retryAt = nextRetryAt();
    if (retryAt === undefined)
      return;
    retryTimer = setTimeout(() => {
      retryTimer = undefined;
      wake();
    }, Math.max(0, retryAt - Date.now()));
  }

  async function loop(run: number): Promise<void> {
    while (isCurrent(run)) {
      const request = get(canRun) ? nextRequest() : undefined;
      if (!request)
        break;
      const days = requestedDays(request);
      markTried(request.asset, days);
      const result = await runRequest(request);
      if (!isCurrent(run))
        return;
      if (isAskedAgain(result))
        forgetTried(request.asset, days);
      else if (result === 'failed') // the unreachable ones wait for their retry instead
        forgetTried(request.asset, days.filter(day => isUnreachable(request.asset, day)));
      if (result === 'cancelled') {
        paused = true;
        break;
      }
      const pacing = nextPacing(isFailure(result), backoff);
      backoff = pacing.backoff;
      set(rateLimited, result === 'rate-limited');
      await delay(pacing.delay);
    }
    if (isCurrent(run)) {
      running = false;
      set(rateLimited, false);
      scheduleRetry();
    }
  }

  function wake(): void {
    if (running || paused || !get(canRun))
      return;
    running = true;
    startPromise(loop(++generation));
  }

  /**
   * Starts over for a new main currency or session: the tried days, the unreachable attempts, the
   * backoff and a user's cancel belong to the old one, and a request still in flight would answer
   * in the old currency.
   */
  function reset(): void {
    generation += 1;
    running = false;
    paused = false;
    set(rateLimited, false);
    clearRetry();
    cancelAll();
    forgetAttempts();
    tried.clear();
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
    givenUpDays,
    rateLimited: readonly(rateLimited),
    register,
  };
});
