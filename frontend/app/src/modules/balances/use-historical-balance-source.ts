import type { ComputedRef } from 'vue';
import type { AggregationContext, AssetBalanceEntries } from '@/modules/balances/aggregation/core/aggregation-types';
import { type BigNumber, bigNumberify } from '@rotki/common';
import { useValueThreshold } from '@/modules/assets/amount-display/use-usd-value-threshold';
import { fromHistoricalEntries, type HistoricalSourceContext } from '@/modules/balances/aggregation/core/historical-source';
import { useHistoricalSnapshotStore } from '@/modules/balances/use-historical-snapshot-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';

interface UseHistoricalBalanceSourceReturn {
  /** The current history-derived balances, priced at current prices, as one aggregation source. */
  source: ComputedRef<AssetBalanceEntries>;
  /** Every held asset regardless of the small-balance threshold, for price discovery. */
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

  const source = computed<AssetBalanceEntries>(() => fromHistoricalEntries(get(entries), context, get(threshold)));
  const unfilteredSource = computed<AssetBalanceEntries>(() => fromHistoricalEntries(get(entries), context, undefined));

  return { source, unfilteredSource };
}
