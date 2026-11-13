import { DAY_SECONDS, type KnownPrice } from '@/modules/statistics/pricing/price-series';

/** The most days one request asks for, so a long history is fetched a few days at a time. */
export const DAYS_PER_REQUEST = 8;

export interface BackfillAsset {
  readonly asset: string;
  /** Prices of the asset in the main currency already cached. */
  readonly known: readonly KnownPrice[];
  /** Times the backend reported as having no price; never asked again. */
  readonly failed: readonly number[];
  /** The times that need a price, unix seconds. */
  readonly times: readonly number[];
}

/**
 * One request for `/balances/historical/asset/prices`: the backend prices
 * `fromTimestamp + i * interval` up to `toTimestamp`, skipping `excludeTimestamps`.
 */
export interface BackfillRequest {
  readonly asset: string;
  readonly fromTimestamp: number;
  readonly toTimestamp: number;
  readonly interval: number;
  readonly excludeTimestamps: number[];
}

/** The start of the UTC day `time` falls in; the oracles keep one price per day. */
export function dayStart(time: number): number {
  return Math.floor(time / DAY_SECONDS) * DAY_SECONDS;
}

/** Whether a known price, or a time known to have none, lies close enough to `time` to settle it. */
function isSettled(entry: Pick<BackfillAsset, 'failed' | 'known'>, time: number): boolean {
  return entry.known.some(point => Math.abs(point.time - time) <= DAY_SECONDS)
    || entry.failed.some(failed => Math.abs(failed - time) <= DAY_SECONDS);
}

/** The days still to fetch for an asset, earliest first. */
function openDays(entry: BackfillAsset): number[] {
  const days = new Set<number>();
  for (const time of entry.times) {
    if (!isSettled(entry, time))
      days.add(dayStart(time));
  }
  return [...days].sort((a, b) => a - b);
}

/**
 * The next request for an asset: its earliest open day and the open days after it, up to
 * {@link DAYS_PER_REQUEST} days later, asked for on a daily grid that skips the days in between.
 */
function nextRequest(entry: BackfillAsset): BackfillRequest | undefined {
  const days = openDays(entry);
  const first = days[0];
  if (first === undefined)
    return undefined;
  const windowEnd = first + (DAYS_PER_REQUEST - 1) * DAY_SECONDS;
  const wanted = new Set(days.filter(day => day <= windowEnd));
  const last = Math.max(...wanted);
  const excludeTimestamps: number[] = [];
  for (let day = first; day <= last; day += DAY_SECONDS) {
    if (!wanted.has(day))
      excludeTimestamps.push(day);
  }
  return { asset: entry.asset, excludeTimestamps, fromTimestamp: first, interval: DAY_SECONDS, toTimestamp: last };
}

/**
 * The next requests worth making, one per asset with days still open.
 *
 * @remarks
 * Each request covers a few days, so the backfill moves forward at the pace the caller sets
 * instead of handing the oracles a whole history at once. A time settles once a price lies within a
 * day of it, or the backend has said it has none.
 *
 * @returns an empty list once every requested time is settled
 */
export function planBackfill(assets: readonly BackfillAsset[]): BackfillRequest[] {
  return assets.flatMap(entry => nextRequest(entry) ?? []);
}
