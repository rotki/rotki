import type { BigNumber } from '@rotki/common';
import type { HistoricalBalanceEntry } from '@/modules/history/balances/types';

/** One account's holding of an asset at one location, optionally inside a protocol. */
export interface HistoricalBucket {
  location: string;
  locationLabel: string | null;
  protocol: string | null;
  amount: BigNumber;
}

export interface HistoricalAssetGroup {
  asset: string;
  amount: BigNumber;
  buckets: HistoricalBucket[];
}

function orNull(value: string | null | undefined): string | null {
  return value === undefined || value === '' ? null : value;
}

function bucketKey({ location, locationLabel, protocol }: HistoricalBucket): string {
  return `${location}|${locationLabel ?? ''}|${protocol ?? ''}`;
}

function byAmountDesc(a: { amount: BigNumber }, b: { amount: BigNumber }): number {
  return b.amount.comparedTo(a.amount) ?? 0;
}

/**
 * Groups the per-bucket entries of a historical balances query by asset.
 *
 * @remarks
 * An empty protocol or account and a missing one name the same bucket, so both are read as `null`
 * and entries that then share a bucket are summed. Buckets are ordered largest first; the groups
 * keep no order, since the table sorts them by value.
 */
export function groupByAsset(entries: HistoricalBalanceEntry[]): HistoricalAssetGroup[] {
  const groups = new Map<string, Map<string, HistoricalBucket>>();

  for (const entry of entries) {
    const bucket: HistoricalBucket = {
      amount: entry.amount,
      location: entry.location,
      locationLabel: orNull(entry.locationLabel),
      protocol: orNull(entry.protocol),
    };
    const buckets = groups.get(entry.asset) ?? new Map<string, HistoricalBucket>();
    const key = bucketKey(bucket);
    const existing = buckets.get(key);
    buckets.set(key, existing ? { ...existing, amount: existing.amount.plus(bucket.amount) } : bucket);
    groups.set(entry.asset, buckets);
  }

  return Array.from(groups.entries(), ([asset, buckets]) => {
    const sorted = [...buckets.values()].sort(byAmountDesc);
    const [first, ...rest] = sorted;
    return {
      amount: rest.reduce((sum, { amount }) => sum.plus(amount), first.amount),
      asset,
      buckets: sorted,
    };
  });
}
