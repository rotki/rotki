import { setDigest } from '@/modules/core/common/data/digest';
import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { PRICE_REFRESH_LANE, UMBRELLA_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';

/** A latest-price query: which assets, and whether it bypasses the cache. */
export interface LatestPricesSubject {
  readonly selectedAssets: readonly string[];
  readonly ignoreCache: boolean;
}

/** One pair's price at one moment. */
export interface HistoricPriceSubject {
  readonly fromAsset: string;
  readonly toAsset: string;
  readonly timestamp: number;
}

/** One asset's daily prices over a range. */
export interface DailyPricesSubject {
  readonly asset: string;
  readonly interval: number;
  readonly fromTimestamp: number;
  readonly toTimestamp: number;
}

/** Whether a query bypasses the cache, as the id part that tells the two runs apart. */
function cachePart(ignoreCache: boolean): ActivityPart {
  return ignoreCache ? ActivityPart.PULL : ActivityPart.CACHED;
}

/**
 * The exchange rates for one main currency.
 *
 * @remarks
 * Keyed by the currency: switching it while the old currency's rates are still in flight starts a
 * second fetch rather than joining the first, which would leave the new currency without a rate.
 * The refresh button reads the `exchange-rates` prefix, so it covers every currency.
 */
export const exchangeRatesActivity = defineActivity<{ currency: string }, readonly [string]>({
  key: subject => [subject.currency],
  kind: ActivityKind.PRICES,
  part: ActivityPart.EXCHANGE_RATES,
});

/**
 * A latest-price query for a set of assets.
 *
 * @remarks
 * `submitTask` dedups by id, so the set has to be part of the identity: under a single
 * `prices:latest` id, opening the manual-balance form while the background sweep was in flight
 * handed the form the sweep's promise, its own batch never ran, and the form showed no price.
 * The set itself cannot go in the id (it is routinely hundreds of assets), so it is folded with
 * `setDigest`, which sorts first so member order never changes the identity.
 *
 * A collision would re-introduce exactly the bug this prevents, for one pair of sets. At the
 * handful of price requests that can be in flight at once, that is far below the noise floor,
 * and the failure is a stale price rather than a wrong one.
 */
export const latestPricesActivity = defineActivity<LatestPricesSubject, readonly [string, ActivityPart]>({
  key: subject => [setDigest(subject.selectedAssets), cachePart(subject.ignoreCache)],
  kind: ActivityKind.PRICES,
  part: ActivityPart.LATEST,
});

/**
 * A balance refresh's latest prices, which also fetches the rates and applies the result.
 *
 * @remarks
 * Its key extends {@link latestPricesActivity}'s with `balances`, so it never joins a plain query
 * of the same set, which neither fetches the rates nor applies anything, while a reader of the
 * `latest` prefix still covers both.
 *
 * The lane runs one refresh at a time, so two overlapping refreshes cannot race their writes.
 */
export const latestPricesRefreshActivity = defineActivity<LatestPricesSubject, readonly [string, ActivityPart, ActivityPart]>({
  key: subject => [setDigest(subject.selectedAssets), cachePart(subject.ignoreCache), ActivityPart.BALANCES],
  kind: ActivityKind.PRICES,
  lane: () => PRICE_REFRESH_LANE,
  part: ActivityPart.LATEST,
});

/** One pair's price at one moment, keyed by all three so distinct queries never dedup. */
export const historicPriceActivity = defineActivity<HistoricPriceSubject, readonly [string, string, number]>({
  key: subject => [subject.fromAsset, subject.toAsset, subject.timestamp],
  kind: ActivityKind.PRICES,
  part: ActivityPart.HISTORIC,
});

/**
 * One batch of historic price queries.
 *
 * @remarks
 * Keyed by a sequence number: each batch is its own request, and nothing reads one by its subject.
 * The leading `batch` part is what lets a progress frame address batches by prefix without driving
 * the single-pair {@link historicPriceActivity} rows beside them.
 */
export const historicPriceBatchActivity = defineActivity<{ sequence: number }, readonly [ActivityPart, number]>({
  key: subject => [ActivityPart.BATCH, subject.sequence],
  kind: ActivityKind.PRICES,
  part: ActivityPart.HISTORIC,
});

/**
 * The umbrella that parents every {@link historicPriceBatchActivity} submitted while it is open.
 *
 * @remarks
 * It sits under the batches' `batch` prefix, so a batch-progress reader covers it too, and runs on
 * the umbrella lane so waiting for its children never holds one of their slots.
 */
export const historicPriceWaveActivity = defineActivity<{ sequence: number }, readonly [ActivityPart, string, number]>({
  key: subject => [ActivityPart.BATCH, 'all', subject.sequence],
  kind: ActivityKind.PRICES,
  lane: () => UMBRELLA_LANE,
  part: ActivityPart.HISTORIC,
});

/** One asset's daily prices over a range. */
export const dailyPricesActivity = defineActivity<DailyPricesSubject, readonly [string, number, number, number]>({
  key: subject => [subject.asset, subject.interval, subject.fromTimestamp, subject.toTimestamp],
  kind: ActivityKind.PRICES,
  part: ActivityPart.DAILY,
});

/**
 * Saving one manual price, keyed by its pair so a save for one asset never joins another's.
 *
 * @remarks
 * A reader of the `manual` prefix (the NFT balances go stale on it) covers it and
 * {@link manualPriceRemoveActivity} together.
 */
export const manualPriceAddActivity = defineActivity<{ fromAsset: string; toAsset: string }, readonly [ActivityPart, string, string]>({
  key: subject => [ActivityPart.ADD, subject.fromAsset, subject.toAsset],
  kind: ActivityKind.PRICES,
  part: ActivityPart.MANUAL,
});

/** Deleting one asset's manual price, keyed by the asset for the same reason. */
export const manualPriceRemoveActivity = defineActivity<{ fromAsset: string }, readonly [ActivityPart, string]>({
  key: subject => [ActivityPart.REMOVE, subject.fromAsset],
  kind: ActivityKind.PRICES,
  part: ActivityPart.MANUAL,
});

/** Building the oracle cache. One at a time, which the producer checks before it submits. */
export const oracleCacheActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.PRICES,
  part: ActivityPart.ORACLE_CACHE,
});
