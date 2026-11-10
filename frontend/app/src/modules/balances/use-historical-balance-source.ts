import type { ComputedRef } from 'vue';
import type { AggregationContext, AssetBalanceEntries } from '@/modules/balances/aggregation/core/aggregation-types';
import type { HistoricalBalanceEntry } from '@/modules/history/balances/types';
import { type BigNumber, bigNumberify } from '@rotki/common';
import { useValueThreshold } from '@/modules/assets/amount-display/use-usd-value-threshold';
import { fromHistoricalEntries, type HistoricalSourceContext } from '@/modules/balances/aggregation/core/historical-source';
import { useBalanceDisplayModeStore } from '@/modules/balances/use-balance-display-mode-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';

interface UseHistoricalBalanceSourceReturn {
  /** True only when the accounting update is on and the user picked history. */
  isHistoryMode: ComputedRef<boolean>;
  /** The current history-derived balances, priced at current prices, as one aggregation source. */
  source: ComputedRef<AssetBalanceEntries>;
  /** Every held asset regardless of the small-balance threshold, for price discovery. */
  unfilteredSource: ComputedRef<AssetBalanceEntries>;
  /** The source for the buckets of the given chains only; empty means every chain. */
  sourceForChains: (chains: readonly string[]) => AssetBalanceEntries;
}

/** Adapts the current history-derived snapshot into an aggregation source. */
export function useHistoricalBalanceSource(
  aggregation: Pick<AggregationContext, 'priceOf' | 'resolveIdentifier'>,
): UseHistoricalBalanceSourceReturn {
  const { entries, isHistoryMode } = storeToRefs(useBalanceDisplayModeStore());
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

  function sourceForChains(chains: readonly string[]): AssetBalanceEntries {
    const selected: HistoricalBalanceEntry[] = get(entries).filter(({ location }) => {
      const chain = matchChain(location);
      return chain !== undefined && (chains.length === 0 || chains.includes(chain));
    });
    return fromHistoricalEntries(selected, context, get(threshold));
  }

  return { isHistoryMode, source, sourceForChains, unfilteredSource };
}
