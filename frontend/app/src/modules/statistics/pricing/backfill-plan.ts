import { SECONDS_PER_DAY } from '@/modules/core/common/constraints';
import { type KnownPrice, nearestWithin } from '@/modules/statistics/pricing/price-series';

/** The most days one request asks for, so a long history is fetched a few days at a time. */
export const DAYS_PER_REQUEST = 8;

export interface BackfillAsset {
  readonly asset: string;
  /** Prices of the asset in the main currency already cached, in time order. */
  readonly known: readonly KnownPrice[];
  /** Days (UTC day starts) the backend reported as having no price, never asked again. */
  readonly failed: ReadonlySet<number>;
  /** The times that need a price, unix seconds. */
  readonly times: readonly number[];
}

/**
 * One request for `/balances/historical/asset/prices`: the backend prices each day from
 * `fromTimestamp` up to `toTimestamp`, skipping `excludeTimestamps`.
 */
export interface BackfillRequest {
  readonly asset: string;
  readonly fromTimestamp: number;
  readonly toTimestamp: number;
  readonly excludeTimestamps: number[];
}

/** The start of the UTC day `time` falls in; the oracles keep one price per day. */
export function dayStart(time: number): number {
  return Math.floor(time / SECONDS_PER_DAY) * SECONDS_PER_DAY;
}

/**
 * How far apart the days of each pass are, coarsest first: one rate a month, then one a week, then
 * every day. A long history gets a rough rate everywhere within minutes, and the daily backfill
 * only refines it.
 */
const PASS_STEPS = [30, 7, 1].map(days => days * SECONDS_PER_DAY);

/** The days still to fetch for an asset, earliest first: those of times with no price within a day. */
function openDays(entry: BackfillAsset): number[] {
  const days = new Set<number>();
  for (const time of entry.times) {
    const day = dayStart(time);
    if (!entry.failed.has(day) && !nearestWithin(entry.known, time, SECONDS_PER_DAY))
      days.add(day);
  }
  return [...days].sort((a, b) => a - b);
}

/** The days that already have a price or are known to have none, in order. */
function settledDays(entry: BackfillAsset): { time: number }[] {
  const days = new Set([...entry.known.map(point => dayStart(point.time)), ...entry.failed]);
  return [...days].sort((a, b) => a - b).map(time => ({ time }));
}

/**
 * The open days a pass picks: walking from the earliest, a day at least `step` away from every
 * settled day and from the day picked before it.
 */
function passDays(open: readonly number[], settled: readonly { time: number }[], step: number): number[] {
  const tolerance = step - SECONDS_PER_DAY;
  const picked: number[] = [];
  for (const day of open) {
    const previous = picked.at(-1);
    if ((previous === undefined || day - previous > tolerance) && !nearestWithin(settled, day, tolerance))
      picked.push(day);
  }
  return picked;
}

/** The days of the next request: the first {@link DAYS_PER_REQUEST} picked by the coarsest pass with any left. */
function nextDays(entry: BackfillAsset): number[] {
  const open = openDays(entry);
  if (open.length === 0)
    return [];
  const settled = settledDays(entry);
  for (const step of PASS_STEPS) {
    const picked = passDays(open, settled, step);
    if (picked.length > 0)
      return picked.slice(0, DAYS_PER_REQUEST);
  }
  return [];
}

/**
 * The next request for an asset, asked for on a daily grid that skips the days in between.
 *
 * @remarks
 * The backend rejects a range that does not end after it starts, so a single day is asked as a
 * two-day grid with the second day excluded.
 */
function nextRequest(entry: BackfillAsset): BackfillRequest | undefined {
  const days = nextDays(entry);
  const first = days[0];
  if (first === undefined)
    return undefined;
  const wanted = new Set(days);
  const last = days.at(-1) ?? first;
  const excludeTimestamps: number[] = [];
  for (let day = first; day <= last; day += SECONDS_PER_DAY) {
    if (!wanted.has(day))
      excludeTimestamps.push(day);
  }
  const singleDay = last === first;
  const toTimestamp = singleDay ? first + SECONDS_PER_DAY : last;
  if (singleDay)
    excludeTimestamps.push(toTimestamp);
  return { asset: entry.asset, excludeTimestamps, fromTimestamp: first, toTimestamp };
}

/**
 * The next requests worth making, one per asset with days still open.
 *
 * @remarks
 * Each request covers a few days, so the backfill moves forward at the pace the caller sets
 * instead of handing the oracles a whole history at once. It works in passes, a day a month, then a
 * week, then every day, so the rates the graph falls back on are never far off. A time settles once
 * a price lies within a day of it, or the backend has said it has none.
 *
 * @returns an empty list once every requested time is settled
 */
export function planBackfill(assets: readonly BackfillAsset[]): BackfillRequest[] {
  return assets.flatMap(entry => nextRequest(entry) ?? []);
}
