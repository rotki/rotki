import type { AssetBalanceWithPriceAndChains, BigNumber } from '@rotki/common';
import type { Balances } from '@/modules/accounts/blockchain-accounts';
import type { AggregationContext } from '@/modules/balances/aggregation/core/aggregation-types';
import type { ExchangeData } from '@/modules/balances/types/exchanges';
import type { ManualBalanceWithValue } from '@/modules/balances/types/manual-balances';
import { get } from '@vueuse/shared';
import { computed, type ComputedRef, type MaybeRefOrGetter, toValue } from 'vue';
import { type BalanceInputs, locationSources } from '@/modules/balances/aggregation/core/location-sources';
import { blockchainValue, locationMapTotals, totalsByChainLocation, totalsByLocation } from '@/modules/balances/aggregation/core/location-totals';
import { summarizeBalances } from '@/modules/balances/aggregation/core/summarize';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { useLocations } from '@/modules/core/common/use-locations';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

interface UseLocationBalancesOptions {
  /** The visible on-chain balances. */
  readonly blockchainBalances: MaybeRefOrGetter<Balances>;
  /** The exchanges and the `banks` location, each keyed by its location. */
  readonly locationBalances: MaybeRefOrGetter<ExchangeData>;
  /** The manual balances, liabilities excluded. */
  readonly manualBalances: MaybeRefOrGetter<readonly ManualBalanceWithValue[]>;
  /** The lookups the aggregation core reads. */
  readonly context: AggregationContext;
}

export interface UseLocationBalancesReturn {
  useLocationBreakdown: (location: MaybeRefOrGetter<string>) => ComputedRef<AssetBalanceWithPriceAndChains[]>;
  balancesByLocation: ComputedRef<Record<string, BigNumber>>;
  balancesByChainLocation: ComputedRef<Record<string, BigNumber>>;
}

/** The balances and totals per trade location, on-chain, exchange, bank and manual alike. */
export function useLocationBalances(options: UseLocationBalancesOptions): UseLocationBalancesReturn {
  const { blockchainBalances, context, locationBalances, manualBalances } = options;
  const { isAssetIgnored } = context;
  const { manualBalanceByLocation } = useManualBalanceData();
  const { tradeLocations } = useLocations();
  const { matchChain } = useSupportedChains();

  const useLocationBreakdown = (location: MaybeRefOrGetter<string>): ComputedRef<AssetBalanceWithPriceAndChains[]> =>
    computed<AssetBalanceWithPriceAndChains[]>(() => {
      const selected = toValue(location);
      const inputs: BalanceInputs = {
        blockchain: toValue(blockchainBalances),
        exchanges: toValue(locationBalances),
        manual: toValue(manualBalances),
      };
      return summarizeBalances(locationSources(selected, inputs, matchChain(selected)), context);
    });

  const balancesByLocation = computed<Record<string, BigNumber>>(() => totalsByLocation(
    blockchainValue(toValue(blockchainBalances), isAssetIgnored),
    locationMapTotals(toValue(locationBalances), isAssetIgnored),
    get(manualBalanceByLocation),
  ));

  /**
   * On-chain totals per chain, keyed by trade-location identifier such as `ethereum`.
   *
   * @remarks
   * What makes a chain discoverable in global search. Kept apart from {@link balancesByLocation} so
   * that its umbrella `blockchain` aggregate stays authoritative for the premium consumers that
   * iterate that map.
   */
  const balancesByChainLocation = computed<Record<string, BigNumber>>(() => totalsByChainLocation(
    toValue(blockchainBalances),
    get(tradeLocations).map(location => location.identifier),
    matchChain,
    isAssetIgnored,
  ));

  return {
    balancesByChainLocation,
    balancesByLocation,
    useLocationBreakdown,
  };
}
