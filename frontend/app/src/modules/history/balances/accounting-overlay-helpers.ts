import { type BigNumber, Zero } from '@rotki/common';

/** Per `(account, asset)` fetch + lookup status, so each row shows its own state. */
export const PairOverlayStatus = {
  EMPTY: 'empty',
  ERROR: 'error',
  LOADING: 'loading',
  PROCESSING: 'processing',
  READY: 'ready',
} as const;

export type PairOverlayStatus = typeof PairOverlayStatus[keyof typeof PairOverlayStatus];

export interface PreparedBucket {
  location: string;
  protocol: string | null;
  times: number[]; // unix seconds, ascending
  values: BigNumber[];
}

export function pairKey(locationLabel: string, asset: string): string {
  return `${locationLabel} ${asset}`;
}

export function resolveStatus(bucketCount: number, processingRequired: boolean): PairOverlayStatus {
  if (bucketCount > 0)
    return PairOverlayStatus.READY;

  return processingRequired ? PairOverlayStatus.PROCESSING : PairOverlayStatus.EMPTY;
}

/** Largest balance value whose timestamp is <= `tsSec` (step function); Zero before the first point. */
export function valueAt(bucket: PreparedBucket, tsSec: number): BigNumber {
  const { times, values } = bucket;
  if (times.length === 0 || tsSec < times[0])
    return Zero;

  let lo = 0;
  let hi = times.length - 1;
  let ans = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (times[mid] <= tsSec) {
      ans = mid;
      lo = mid + 1;
    }
    else {
      hi = mid - 1;
    }
  }
  return ans >= 0 ? values[ans] : Zero;
}

/**
 * Two entries that share a `(location, protocol)` scope are the same logical position — the
 * backend sometimes splits one position across several entries (e.g. a plain-wallet series
 * tagged `null` for an early window and `''` for a later one). Treating them as separate
 * buckets double-counts: `valueAt` holds each series' last value forever, so a recent event
 * sums the stale early segment onto the current one. Merging their points into one ordered
 * step-function fixes both the total and the per-scope breakdown row.
 */
export function mergeSameScopeBuckets(buckets: PreparedBucket[]): PreparedBucket[] {
  const byScope = new Map<string, PreparedBucket>();
  for (const bucket of buckets) {
    const key = `${bucket.location}|${bucket.protocol ?? ''}`;
    const existing = byScope.get(key);
    if (!existing) {
      byScope.set(key, { ...bucket, times: [...bucket.times], values: [...bucket.values] });
      continue;
    }
    const points = existing.times.map((time, i) => ({ time, value: existing.values[i] }));
    bucket.times.forEach((time, i) => points.push({ time, value: bucket.values[i] }));
    points.sort((a, b) => a.time - b.time);
    const times: number[] = [];
    const values: BigNumber[] = [];
    for (const { time, value } of points) {
      if (times.length > 0 && times.at(-1) === time) {
        values[values.length - 1] = value; // same timestamp: later entry wins
      }
      else {
        times.push(time);
        values.push(value);
      }
    }
    byScope.set(key, { location: existing.location, protocol: existing.protocol, times, values });
  }
  return [...byScope.values()];
}
