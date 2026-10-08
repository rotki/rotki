import type { HistoricalBucket } from '@/modules/statistics/historical-balances/historical-balances-grouping';
import { type BigNumber, Zero } from '@rotki/common';
import { groupBy } from 'plainfp/arrays';
import { type HistoricalAssetRow, PriceStatus } from '@/modules/statistics/historical-balances/use-historical-balance-values';

export const HistoricalBalancesMode = {
  /** Every member of an asset collection folded into one row. */
  COLLECTION: 'collection',
  /** One row per asset identifier. */
  FLAT: 'flat',
} as const;

export type HistoricalBalancesMode = typeof HistoricalBalancesMode[keyof typeof HistoricalBalancesMode];

/** One bucket as the expansion shows it, valued at its own asset's price. */
export interface HistoricalBucketRow extends HistoricalBucket {
  asset: string;
  priceStatus: PriceStatus;
  value: BigNumber | undefined;
}

export interface HistoricalBalanceRow {
  /** The asset, or the main asset of a collection row. */
  asset: string;
  amount: BigNumber;
  /** For a collection row, the average price of its priced members. */
  price: BigNumber | undefined;
  value: BigNumber | undefined;
  priceStatus: PriceStatus;
  buckets: HistoricalBucketRow[];
  /** The assets folded into this row; more than one only for a collection. */
  members: string[];
  /** Some members have no value, so `value` covers only the priced ones. */
  partial: boolean;
}

export interface HistoricalBalancesFilter {
  locations: readonly string[];
  accounts: readonly string[];
  /** Keeps an asset by its identifier; undefined keeps them all. */
  matchesAsset?: (asset: string) => boolean;
}

export interface HistoricalBalancesSummary {
  /** The sum of every priced row. */
  total: BigNumber;
  pendingCount: number;
  missingCount: number;
  spamCount: number;
}

interface CollectionLookup {
  collectionOf: (asset: string) => string | null | undefined;
  mainAssetOf: (collectionId: string) => string | undefined;
}

/** Where a row falls before its value is compared: priced rows first, spam last. */
const STATUS_RANK: Readonly<Record<PriceStatus, number>> = {
  [PriceStatus.PRICED]: 0,
  [PriceStatus.PENDING]: 1,
  [PriceStatus.MISSING]: 2,
  [PriceStatus.SPAM]: 3,
};

/**
 * Priced rows first by value, then rows still loading, then those with no price, then spam; each
 * group without a value by amount. A price arriving moves its row up once rather than the whole
 * table reshuffling while prices load.
 */
export function sortRows(rows: readonly HistoricalBalanceRow[]): HistoricalBalanceRow[] {
  return [...rows].sort((a, b) => {
    const byStatus = STATUS_RANK[a.priceStatus] - STATUS_RANK[b.priceStatus];
    if (byStatus !== 0)
      return byStatus;
    if (a.value && b.value)
      return b.value.comparedTo(a.value) ?? 0;
    return b.amount.comparedTo(a.amount) ?? 0;
  });
}

function sumAmounts(items: readonly { amount: BigNumber }[]): BigNumber {
  return items.reduce((sum, { amount }) => sum.plus(amount), Zero);
}

/**
 * Narrows each row to the buckets on the chosen locations and accounts, and the rows to the chosen
 * assets.
 *
 * @remarks
 * A row's amount and value are recomputed from the buckets it keeps, at the price it already has, so
 * changing a filter never asks for a price again. A row left with no buckets is dropped. A bucket
 * with no account never matches an account filter.
 */
export function filterRows(rows: readonly HistoricalAssetRow[], filter: HistoricalBalancesFilter): HistoricalAssetRow[] {
  const { accounts, locations, matchesAsset } = filter;
  const filtersBuckets = locations.length > 0 || accounts.length > 0;

  const keepsBucket = ({ location, locationLabel }: HistoricalBucket): boolean =>
    (locations.length === 0 || locations.includes(location))
    && (accounts.length === 0 || (locationLabel !== null && accounts.includes(locationLabel)));

  return rows.flatMap((row) => {
    if (matchesAsset && !matchesAsset(row.asset))
      return [];
    if (!filtersBuckets)
      return [row];
    const buckets = row.buckets.filter(keepsBucket);
    if (buckets.length === 0)
      return [];
    const amount = sumAmounts(buckets);
    return [{ ...row, amount, buckets, value: row.price ? amount.times(row.price) : undefined }];
  });
}

/** The total and the counts of rows still waiting for, or never getting, a price. */
export function summarize(rows: readonly HistoricalAssetRow[]): HistoricalBalancesSummary {
  const countOf = (status: PriceStatus): number => rows.filter(row => row.priceStatus === status).length;
  return {
    missingCount: countOf(PriceStatus.MISSING),
    pendingCount: countOf(PriceStatus.PENDING),
    spamCount: countOf(PriceStatus.SPAM),
    total: rows.reduce((sum, { value }) => (value ? sum.plus(value) : sum), Zero),
  };
}

function toBalanceRow(row: HistoricalAssetRow): HistoricalBalanceRow {
  return {
    ...row,
    buckets: row.buckets.map(bucket => ({
      ...bucket,
      asset: row.asset,
      priceStatus: row.priceStatus,
      value: row.price ? bucket.amount.times(row.price) : undefined,
    })),
    members: [row.asset],
    partial: false,
  };
}

/** Pending while any member is, priced when any member is, spam only when every member is. */
function collectionStatus(members: readonly HistoricalAssetRow[]): PriceStatus {
  const has = (status: PriceStatus): boolean => members.some(member => member.priceStatus === status);
  if (has(PriceStatus.PENDING))
    return PriceStatus.PENDING;
  if (has(PriceStatus.PRICED))
    return PriceStatus.PRICED;
  if (members.every(member => member.priceStatus === PriceStatus.SPAM))
    return PriceStatus.SPAM;
  return PriceStatus.MISSING;
}

/** Folds a collection's members into one row headed by its main asset. */
function collapse(mainAsset: string, members: readonly HistoricalAssetRow[]): HistoricalBalanceRow {
  const priceStatus = collectionStatus(members);
  const priced = members.filter(member => member.priceStatus === PriceStatus.PRICED);
  const pricedAmount = sumAmounts(priced);
  const value = priceStatus === PriceStatus.PRICED
    ? priced.reduce((sum, member) => (member.value ? sum.plus(member.value) : sum), Zero)
    : undefined;

  return {
    amount: sumAmounts(members),
    asset: mainAsset,
    buckets: members
      .flatMap(member => toBalanceRow(member).buckets)
      .sort((a, b) => b.amount.comparedTo(a.amount) ?? 0),
    members: members.map(member => member.asset),
    partial: priceStatus === PriceStatus.PRICED && priced.length < members.length,
    price: value && !pricedAmount.isZero() ? value.div(pricedAmount) : undefined,
    priceStatus,
    value,
  };
}

/**
 * The rows the table shows: one per asset, or with each asset collection folded into one row.
 *
 * @remarks
 * Members of a collection are the same asset on different chains, so their amounts add up. Each
 * keeps its own price, so a collection's value is the sum of its members' values. An asset whose
 * collection is not known yet, a collection whose main asset is not known, and a collection with a
 * single member held all stay as rows of their own.
 */
export function toViewRows(
  rows: readonly HistoricalAssetRow[],
  mode: HistoricalBalancesMode,
  lookup: CollectionLookup,
): HistoricalBalanceRow[] {
  if (mode === HistoricalBalancesMode.FLAT)
    return rows.map(toBalanceRow);

  const standalone: HistoricalAssetRow[] = [];
  const collected: { collectionId: string; row: HistoricalAssetRow }[] = [];
  for (const row of rows) {
    const collectionId = lookup.collectionOf(row.asset);
    if (collectionId)
      collected.push({ collectionId, row });
    else
      standalone.push(row);
  }

  const byCollection = groupBy(collected, ({ collectionId }) => collectionId);
  return [
    ...standalone.map(toBalanceRow),
    ...Object.entries(byCollection).flatMap(([collectionId, entries]) => {
      const members = entries.map(({ row }) => row);
      const mainAsset = lookup.mainAssetOf(collectionId);
      return mainAsset && members.length > 1 ? [collapse(mainAsset, members)] : members.map(toBalanceRow);
    }),
  ];
}
