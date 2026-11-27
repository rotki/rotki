import type { HistoricalBalanceEntry, HistoricalBalanceSeriesResponse } from '@/modules/history/balances/types';
import { type BigNumber, Zero } from '@rotki/common';

type SeriesEntry = HistoricalBalanceSeriesResponse['entries'][number];

export interface BalancePoint {
  /** unix seconds */
  readonly time: number;
  readonly value: BigNumber;
}

/** One account's balance of one asset, held in one location under one protocol. */
export interface BucketSeries {
  readonly key: string;
  readonly location: string;
  /** Absent for the plain wallet balance, outside any protocol. */
  readonly protocol: string | undefined;
  readonly points: readonly BalancePoint[];
}

/** The window a series covers, in unix seconds. A `from` of 0 means since the first event. */
export interface SeriesRange {
  readonly from: number;
  readonly to: number;
}

export interface BalanceSummary {
  readonly current: BigNumber;
  readonly start: BigNumber;
  readonly change: BigNumber;
}

function bucketKey(location: string, protocol: string | null | undefined): string {
  return `${location}:${protocol ?? ''}`;
}

/**
 * Appends a point, replacing the last one when it falls on the same second.
 *
 * @remarks
 * The backend sends one point per event, and several events can share a second. Only the balance
 * after the last of them is a balance the account held, so the earlier ones are dropped.
 */
function pushPoint(points: BalancePoint[], point: BalancePoint): void {
  const last = points.at(-1);
  if (last?.time === point.time)
    points[points.length - 1] = point;
  else
    points.push(point);
}

/**
 * Builds the step series of every bucket over a range.
 *
 * @remarks
 * The series endpoint only returns the events inside the range, so a bucket starts from its balance
 * just before the range (`opening`), and a bucket with no event in the range is a flat line at that
 * balance. Every series is carried to the end of the range, so a step line reaches the present
 * instead of stopping at the last event.
 *
 * @param opening - the buckets' balances just before `range.from`; empty when the range is unbounded
 * @param series - the per-bucket points inside the range
 */
export function buildBucketSeries(
  opening: readonly HistoricalBalanceEntry[],
  series: readonly SeriesEntry[],
  range: SeriesRange,
): BucketSeries[] {
  const buckets = new Map<string, { location: string; protocol: string | undefined; points: BalancePoint[] }>();

  function bucketFor(location: string, protocol: string | null | undefined): BalancePoint[] {
    const key = bucketKey(location, protocol);
    let bucket = buckets.get(key);
    if (!bucket) {
      bucket = { location, points: [], protocol: protocol ?? undefined };
      buckets.set(key, bucket);
    }
    return bucket.points;
  }

  for (const entry of opening)
    pushPoint(bucketFor(entry.location, entry.protocol), { time: range.from, value: entry.amount });

  for (const entry of series) {
    const points = bucketFor(entry.location, entry.protocol);
    entry.times.forEach((time, index) => {
      const value = entry.values[index];
      if (value !== undefined)
        pushPoint(points, { time, value });
    });
  }

  return Array.from(buckets.entries(), ([key, { location, points, protocol }]) => {
    const last = points.at(-1);
    if (last && last.time < range.to)
      points.push({ time: range.to, value: last.value });
    return { key, location, points, protocol };
  })
    .sort((a, b) => a.key.localeCompare(b.key));
}

/** Every bucket's value at each of a shared set of times. */
export interface AlignedBuckets {
  /** unix seconds, ascending */
  readonly times: readonly number[];
  /** One row per bucket, in bucket order, holding a value for each of `times`. */
  readonly rows: readonly (readonly BigNumber[])[];
}

/**
 * Puts every bucket on the times at which any bucket changes.
 *
 * @remarks
 * A step series holds its value until its next point, so a bucket's value at a time is its latest
 * point at or before it, and zero before its first point. Stacking the buckets in a chart needs this:
 * a stacked series adds up values by position, so each must have a value at the same times.
 */
export function alignBuckets(buckets: readonly BucketSeries[]): AlignedBuckets {
  const times = [...new Set(buckets.flatMap(bucket => bucket.points.map(point => point.time)))].sort((a, b) => a - b);
  const rows = buckets.map((bucket) => {
    let cursor = -1;
    return times.map((time) => {
      while ((bucket.points[cursor + 1]?.time ?? Infinity) <= time)
        cursor++;
      return bucket.points[cursor]?.value ?? Zero;
    });
  });
  return { rows, times };
}

/** Adds the buckets up into one step series. */
export function totalSeries(buckets: readonly BucketSeries[]): BalancePoint[] {
  const { rows, times } = alignBuckets(buckets);
  return times.map((time, index) => ({
    time,
    value: rows.reduce((sum, row) => sum.plus(row[index] ?? Zero), Zero),
  }));
}

/**
 * The balance at the start and end of the range, and how it moved between them.
 *
 * @remarks
 * The start is the balance held at `from`. A total whose first point comes later began the range
 * empty, so its start is zero rather than that first balance.
 *
 * @param total - the account's total balance series over the range
 * @param from - the range start, unix seconds
 */
export function summarize(total: readonly BalancePoint[], from: number): BalanceSummary {
  const first = total.at(0);
  const start = first?.time === from ? first.value : Zero;
  const current = total.at(-1)?.value ?? Zero;
  return { change: current.minus(start), current, start };
}
