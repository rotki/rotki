import type { BigNumber } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { HistoricalAssetGroup } from '@/modules/statistics/historical-balances/historical-balances-grouping';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { useAssetInfoCache } from '@/modules/assets/use-asset-info-cache';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';

/** How many assets are priced per request; the next batch goes out once this one has settled. */
export const PRICE_BATCH_SIZE = 50;

export const PriceStatus = {
  /** Priced; `price` and `value` are set. */
  PRICED: 'priced',
  /** Waiting for its asset info, its turn in the batch queue, or the price itself. */
  PENDING: 'pending',
  /** The price came back empty, so the asset is left out of the total. */
  MISSING: 'missing',
  /** Marked as spam, so it is never priced. */
  SPAM: 'spam',
} as const;

export type PriceStatus = typeof PriceStatus[keyof typeof PriceStatus];

export interface HistoricalAssetRow extends HistoricalAssetGroup {
  /** The asset's price in the user's currency at the as-of time; set only when `priceStatus` is priced. */
  price: BigNumber | undefined;
  /** `amount` at `price`; set only when `priceStatus` is priced. */
  value: BigNumber | undefined;
  priceStatus: PriceStatus;
}

interface UseHistoricalBalanceValuesReturn {
  rows: ComputedRef<HistoricalAssetRow[]>;
}

/**
 * Values each asset group at its historic price at the as-of time.
 *
 * @remarks
 * Spam assets are never priced: most have no market, and asking the oracles about hundreds of them
 * is what made a whole page of prices wait minutes. An asset is only classified once its info has
 * loaded, so a spam asset is never priced by getting there first.
 *
 * The rest are released to the historic price cache {@link PRICE_BATCH_SIZE} at a time, the next
 * batch once every released price has settled, so values fill in as they arrive instead of all at
 * the end, and the backend is never handed every asset in one request. Reading a price is what
 * queues its fetch, which is why only released assets are read. Prices come back in the user's
 * currency, so no conversion follows.
 *
 * @param groups - the asset groups to value
 * @param timestamp - the as-of time in unix seconds
 */
export function useHistoricalBalanceValues(
  groups: MaybeRefOrGetter<HistoricalAssetGroup[]>,
  timestamp: MaybeRefOrGetter<number>,
): UseHistoricalBalanceValuesReturn {
  const released = shallowRef<ReadonlySet<string>>(new Set());

  const { createKey, getHistoricPrice, getIsPending } = useHistoricPriceCache();
  const { getAssetInfo } = useAssetInfoRetrieval();
  const { isPending: isAssetInfoPending } = useAssetInfoCache();

  /** Spam, priceable, or not known yet because its info is still loading. */
  function classify(asset: string): 'spam' | 'priceable' | 'unknown' {
    const info = getAssetInfo(asset);
    if (info?.isSpam)
      return 'spam';
    if (!info?.resolved && get(isAssetInfoPending(asset)))
      return 'unknown';
    return 'priceable';
  }

  function priceRow(group: HistoricalAssetGroup, at: number): HistoricalAssetRow {
    const pending = { ...group, price: undefined, priceStatus: PriceStatus.PENDING, value: undefined };
    if (!get(released).has(group.asset))
      return pending;
    const price = getHistoricPrice(group.asset, at);
    if (getIsPending(createKey(group.asset, at)))
      return pending;
    if (!price.isPositive())
      return { ...group, price: undefined, priceStatus: PriceStatus.MISSING, value: undefined };
    return { ...group, price, priceStatus: PriceStatus.PRICED, value: group.amount.times(price) };
  }

  const classified = computed<{ group: HistoricalAssetGroup; kind: ReturnType<typeof classify> }[]>(() =>
    toValue(groups).map(group => ({ group, kind: classify(group.asset) })));

  const rows = computed<HistoricalAssetRow[]>(() => {
    const at = toValue(timestamp);
    return get(classified).map(({ group, kind }) => (kind === 'spam'
      ? { ...group, price: undefined, priceStatus: PriceStatus.SPAM, value: undefined }
      : priceRow(group, at)));
  });

  /** Every released price has come back, so the next batch can go out. */
  const batchSettled = computed<boolean>(() => get(rows).every(row => row.priceStatus !== PriceStatus.PENDING || !get(released).has(row.asset)));

  function releaseNextBatch(): void {
    const current = get(released);
    const next = get(classified)
      .filter(({ group, kind }) => kind === 'priceable' && !current.has(group.asset))
      .slice(0, PRICE_BATCH_SIZE)
      .map(({ group }) => group.asset);
    if (next.length > 0)
      set(released, new Set([...current, ...next]));
  }

  watch([(): HistoricalAssetGroup[] => toValue(groups), (): number => toValue(timestamp)], () => {
    set(released, new Set());
  });

  watchImmediate([batchSettled, classified, released], () => {
    if (get(batchSettled))
      releaseNextBatch();
  });

  return { rows };
}
