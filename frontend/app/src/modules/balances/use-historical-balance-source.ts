import type { ComputedRef } from 'vue';
import type { AggregationContext, AssetBalanceEntries } from '@/modules/balances/aggregation/core/aggregation-types';
import type { HistoricalBalanceEntry } from '@/modules/history/balances/types';
import { type BigNumber, bigNumberify } from '@rotki/common';
import { useValueThreshold } from '@/modules/assets/amount-display/use-usd-value-threshold';
import { fromHistoricalEntries, type HistoricalSourceContext, visibleHistoricalEntries } from '@/modules/balances/aggregation/core/historical-source';
import { useHistoricalSnapshotStore } from '@/modules/balances/use-historical-snapshot-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';

interface UseHistoricalBalanceSourceReturn {
  /** The asset buckets every history surface shows: small chain balances, liabilities and bank buckets left out. */
  visibleEntries: ComputedRef<HistoricalBalanceEntry[]>;
  /** The liability buckets (e.g. ERC-20 debt tokens) visible after threshold filtering. */
  visibleLiabilityEntries: ComputedRef<HistoricalBalanceEntry[]>;
  /** Resolved identifiers of every liability bucket in the snapshot, before threshold filtering. */
  liabilityAssets: ComputedRef<ReadonlySet<string>>;
  /** The visible asset buckets, priced at current prices, as one aggregation source. */
  source: ComputedRef<AssetBalanceEntries>;
  /** The visible liability buckets, priced at current prices, as one aggregation source. */
  liabilitySource: ComputedRef<AssetBalanceEntries>;
  /** Every held asset and liability regardless of the small-balance threshold, for price discovery. */
  unfilteredSource: ComputedRef<AssetBalanceEntries>;
}

/** Adapts the current history-derived snapshot into an aggregation source. */
export function useHistoricalBalanceSource(
  aggregation: Pick<AggregationContext, 'priceOf' | 'resolveIdentifier'>,
): UseHistoricalBalanceSourceReturn {
  const { entries } = storeToRefs(useHistoricalSnapshotStore());
  const { matchChain } = useSupportedChains();
  const thresholdSetting = useValueThreshold(BalanceSource.BLOCKCHAIN);

  const context: HistoricalSourceContext = {
    matchChain,
    priceOf: aggregation.priceOf,
    resolveIdentifier: aggregation.resolveIdentifier,
  };

  const threshold = computed<BigNumber | undefined>(() => {
    const value = get(thresholdSetting);
    return value === undefined ? undefined : bigNumberify(value);
  });

  const allVisibleEntries = computed<HistoricalBalanceEntry[]>(() => visibleHistoricalEntries(get(entries), context, get(threshold)));
  const visibleEntries = computed<HistoricalBalanceEntry[]>(() => get(allVisibleEntries).filter(entry => !entry.isLiability));
  const visibleLiabilityEntries = computed<HistoricalBalanceEntry[]>(() => get(allVisibleEntries).filter(entry => entry.isLiability === true));
  const liabilityAssets = computed<ReadonlySet<string>>(() => new Set(
    get(entries)
      .filter(entry => entry.isLiability === true)
      .map(entry => context.resolveIdentifier(entry.asset)),
  ));
  const source = computed<AssetBalanceEntries>(() => fromHistoricalEntries(get(visibleEntries), context));
  const liabilitySource = computed<AssetBalanceEntries>(() => fromHistoricalEntries(get(visibleLiabilityEntries), context));
  const unfilteredSource = computed<AssetBalanceEntries>(() => fromHistoricalEntries(get(entries), context));

  return { liabilityAssets, liabilitySource, source, unfilteredSource, visibleEntries, visibleLiabilityEntries };
}
