import type { FailedHistoricalAssetPriceResponse, HistoricalAssetPriceResponse } from '@rotki/common';
import { get, set } from '@vueuse/shared';
import { pipe } from 'plainfp';
import { isErr, tap, tapError } from 'plainfp/result';
import { shallowRef } from 'vue';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { logger } from '@/modules/core/common/logging/logging';
import { useSetting } from '@/modules/settings/use-setting';
import { classifyOutcome, type RequestResult } from '@/modules/statistics/pricing/backfill-outcome';
import { BACKOFF_MAX_MS, BACKOFF_START_MS } from '@/modules/statistics/pricing/backfill-pacing';
import { type BackfillRequest, dayStart, requestedDays } from '@/modules/statistics/pricing/backfill-plan';
import { useBackfillTask } from '@/modules/statistics/pricing/use-backfill-task';
import { usePriceSeriesStore } from '@/modules/statistics/pricing/use-price-series-store';

interface UseBackfillRequestsReturn {
  /** Runs one request and files its prices and its days without one. */
  readonly runRequest: (request: BackfillRequest) => Promise<RequestResult>;
  /** Cancels every backfill request in flight. */
  readonly cancelAll: () => void;
  /**
   * The days of an asset the backfill gave up on this session, because they stayed unreachable.
   * Reactive, so a computed reading it updates when a day is given up on.
   */
  readonly givenUpDays: (asset: string) => ReadonlySet<number>;
  /** The unreachable days of an asset that wait for their next try. */
  readonly waitingDays: (asset: string) => ReadonlySet<number>;
  /** When the next waiting day may be asked for again, in milliseconds, or undefined if none waits. */
  readonly nextRetryAt: () => number | undefined;
  /** Whether a day came back unreachable and is still asked for again. */
  readonly isUnreachable: (asset: string, day: number) => boolean;
  /** Forgets which days came back unreachable and since when, for a new main currency or session. */
  readonly forgetAttempts: () => void;
}

/**
 * A day an oracle could not be reached for: how often, when to ask again, and the answer by which
 * the backend has surely penalized the failing oracles.
 */
interface Unreachable {
  readonly attempts: number;
  readonly retryAt: number;
  /** When the day came back unreachable one time more than the penalty threshold, if it did yet. */
  readonly penalizedBy?: number;
}

/** The wait after the n-th unreachable answer for a day: doubling from the first backoff, capped. */
function retryDelay(attempts: number): number {
  return Math.min(BACKOFF_MAX_MS, BACKOFF_START_MS * 2 ** (attempts - 1));
}

/**
 * The next note for a day that came back unreachable again, or for the first time. The backend
 * penalizes an oracle on the failure after `threshold` in a row, and every request for the day
 * that failed counted as one, so a penalty began by its `threshold + 1`-th unreachable answer.
 */
function noteUnreachable(previous: Unreachable | undefined, now: number, threshold: number): Unreachable {
  const attempts = (previous?.attempts ?? 0) + 1;
  const penalizedBy = previous?.penalizedBy ?? (attempts > threshold ? now : undefined);
  return { attempts, penalizedBy, retryAt: now + retryDelay(attempts) };
}

const EMPTY_FAILURES: FailedHistoricalAssetPriceResponse = {
  failedPricesTimestamps: [],
  noPricesTimestamps: [],
  rateLimitedPricesTimestamps: [],
};

/** The UTC days an answer has a price for. */
function pricedDays(response: HistoricalAssetPriceResponse): ReadonlySet<number> {
  return new Set(Object.keys(response.prices).map(time => dayStart(Number(time))));
}

/** The distinct times not on one of the given days. */
function unpriced(times: readonly number[], priced: ReadonlySet<number>): number[] {
  return [...new Set(times)].filter(time => !priced.has(dayStart(time)));
}

function isEmpty(entry: FailedHistoricalAssetPriceResponse): boolean {
  return entry.failedPricesTimestamps.length === 0 && entry.noPricesTimestamps.length === 0 && entry.rateLimitedPricesTimestamps.length === 0;
}

/**
 * Runs backfill requests against `/balances/historical/asset/prices` as task center activities.
 *
 * @remarks
 * The backend prices in whatever main currency is set when it answers, so a response that arrives
 * after a currency switch is dropped rather than filed under the new currency. Days the backend
 * reports as having no price are recorded, so the user can add them by hand.
 *
 * A day that comes back unreachable waits before it is asked for again, longer after each answer,
 * while the other days go ahead. The backend penalizes an oracle once it failed more times in a row
 * than the penalty threshold, so a penalty began by the day's answer after that many, and the day
 * is asked for again until that answer is older than the penalty duration plus the first backoff.
 * The backend skips a penalized oracle for that long and reports its days unreachable meanwhile,
 * so giving up sooner would give up inside a penalty. Without a limit, an oracle the user's network can never reach would hold the
 * same days in the queue all session. A day given up on is filed with the days that could not be
 * fetched, not the ones without a price: the daily price fetcher still asks for it, and the user
 * can still price it by hand.
 */
export function useBackfillRequests(): UseBackfillRequestsReturn {
  const currencySymbol = useSetting('currencySymbol');
  const oraclePenaltyDuration = useSetting('oraclePenaltyDuration');
  const oraclePenaltyThresholdCount = useSetting('oraclePenaltyThresholdCount');
  const store = usePriceSeriesStore();
  const { failedDailyPrices } = useHistoricPriceCache();
  const { cancelAll, submitBackfill } = useBackfillTask();

  /** Per asset, the days (unix seconds) that came back unreachable and are still asked for. */
  const unreachable = new Map<string, Map<number, Unreachable>>();
  /** Per asset, the days that stayed unreachable for longer than an oracle penalty. */
  const givenUp = shallowRef<ReadonlyMap<string, ReadonlySet<number>>>(new Map());

  /**
   * Notes this answer's unreachable days and returns the ones unreachable for a whole penalty.
   * Days it priced or reported without a price are settled, so they are no longer waited on. A
   * rate-limited day keeps its note, so a day that alternates between the two is still given up.
   */
  function giveUpOn(asset: string, response: FailedHistoricalAssetPriceResponse & Pick<HistoricalAssetPriceResponse, 'prices'>): number[] {
    const days = unreachable.get(asset) ?? new Map<number, Unreachable>();
    unreachable.set(asset, days);
    const failed = new Set(response.failedPricesTimestamps);
    for (const day of [...Object.keys(response.prices).map(Number), ...response.noPricesTimestamps])
      days.delete(day);
    const now = Date.now();
    // one more try once the penalty is surely over, as the backend still applies it at its last second
    const window = get(oraclePenaltyDuration) * 1000 + BACKOFF_START_MS;
    const exhausted: number[] = [];
    for (const time of failed) {
      const note = noteUnreachable(days.get(time), now, get(oraclePenaltyThresholdCount));
      if (note.penalizedBy !== undefined && now - note.penalizedBy > window) {
        days.delete(time);
        exhausted.push(time);
      }
      else {
        days.set(time, note);
      }
    }
    if (exhausted.length > 0)
      set(givenUp, new Map([...get(givenUp), [asset, new Set([...givenUpDays(asset), ...exhausted])]]));
    return exhausted;
  }

  function givenUpDays(asset: string): ReadonlySet<number> {
    return get(givenUp).get(asset) ?? new Set<number>();
  }

  function waitingDays(asset: string): ReadonlySet<number> {
    const now = Date.now();
    const waiting = new Set<number>();
    for (const [day, { retryAt }] of unreachable.get(asset) ?? []) {
      if (retryAt > now)
        waiting.add(day);
    }
    return waiting;
  }

  function isUnreachable(asset: string, day: number): boolean {
    return unreachable.get(asset)?.has(day) ?? false;
  }

  /**
   * A request that never got an answer files its days as unreachable when it failed on the
   * network, and otherwise only the ones that came back unreachable before: they wait for
   * another try and are given up on in time, instead of staying unasked and unfiled for the
   * session.
   */
  function noteFailedRequest(request: BackfillRequest, result: RequestResult): void {
    const days = requestedDays(request).filter(day => result === 'unreachable' || isUnreachable(request.asset, day));
    if (days.length > 0)
      recordFailures(request.asset, { failedPricesTimestamps: days, noPricesTimestamps: [], prices: {}, rateLimitedPricesTimestamps: [] });
  }

  function nextRetryAt(): number | undefined {
    const now = Date.now();
    let next: number | undefined;
    for (const days of unreachable.values()) {
      for (const { retryAt } of days.values()) {
        if (retryAt > now && (next === undefined || retryAt < next))
          next = retryAt;
      }
    }
    return next;
  }

  /**
   * Files the days without a price, and takes the days it priced off every list.
   *
   * @remarks
   * The unreachable days are left out until the backfill gives up on them, since it asks for them
   * again itself; then they join the days that could not be fetched. The failed and rate-limited
   * lists otherwise belong to the daily price fetcher, which shows them for the last fetch it made,
   * so the entries already there are kept, except for the days this answer priced. An asset with
   * nothing left on any list loses its entry.
   */
  function recordFailures(asset: string, response: HistoricalAssetPriceResponse): void {
    const exhausted = giveUpOn(asset, response);
    const current = get(failedDailyPrices);
    const previous = current[asset] ?? EMPTY_FAILURES;
    const priced = pricedDays(response);
    if (response.noPricesTimestamps.length === 0 && exhausted.length === 0 && (isEmpty(previous) || priced.size === 0))
      return;

    // a day this answer settled leaves the lists it was on before, so it sits on one list only
    const noPrice = new Set([...priced, ...response.noPricesTimestamps.map(dayStart)]);
    const gaveUp = new Set([...priced, ...exhausted.map(dayStart)]);
    const settled = new Set([...noPrice, ...gaveUp]);
    const entry: FailedHistoricalAssetPriceResponse = {
      failedPricesTimestamps: [...new Set([...unpriced(previous.failedPricesTimestamps, noPrice), ...exhausted])],
      noPricesTimestamps: [...new Set([...unpriced(previous.noPricesTimestamps, gaveUp), ...response.noPricesTimestamps])],
      rateLimitedPricesTimestamps: unpriced(previous.rateLimitedPricesTimestamps, settled),
    };
    const others = { ...current };
    delete others[asset];
    set(failedDailyPrices, isEmpty(entry) ? others : { ...others, [asset]: entry });
  }

  function forgetAttempts(): void {
    unreachable.clear();
    set(givenUp, new Map());
  }

  async function runRequest(request: BackfillRequest): Promise<RequestResult> {
    const currency = get(currencySymbol);
    const outcome = await submitBackfill(request);
    if (get(currencySymbol) !== currency)
      return 'stale';
    const result = classifyOutcome(outcome);
    pipe(
      outcome,
      tap((response) => {
        store.addPrices(request.asset, Object.entries(response.prices).map(([time, price]) => ({ price, time: Number(time) })));
        recordFailures(request.asset, response);
      }),
      tapError((error) => {
        if (result !== 'cancelled')
          logger.error(error.message);
      }),
    );
    if (isErr(outcome) && (result === 'failed' || result === 'unreachable'))
      noteFailedRequest(request, result);
    return result;
  }

  return { cancelAll, forgetAttempts, givenUpDays, isUnreachable, nextRetryAt, runRequest, waitingDays };
}
