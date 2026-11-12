import type { ComputedRef } from 'vue';
import type { HoldingsSummary, LocationHolding } from '@/modules/dashboard/holdings/core/holdings-types';
import type { HoldingsInputs } from '@/modules/dashboard/holdings/use-holdings-contributions';
import { mergeLocations } from '@/modules/dashboard/holdings/core/location-holdings';
import { summarizeSources } from '@/modules/dashboard/holdings/core/source-summary';
import { useViewHoldingsContributions } from '@/modules/dashboard/holdings/use-history-holdings-contributions';

interface UseDashboardHoldingsReturn {
  readonly summary: ComputedRef<HoldingsSummary>;
  readonly holdings: ComputedRef<LocationHolding[]>;
}

/** Net worth broken down by source kind and by place, in the dashboard's balance view. */
export function useDashboardHoldings(inputs: HoldingsInputs = useViewHoldingsContributions()): UseDashboardHoldingsReturn {
  const { contributions, liabilities, liabilitiesExcluded, locationOfChain, nfts, placeRank } = inputs;

  return {
    holdings: computed<LocationHolding[]>(() => mergeLocations(get(contributions), { locationOfChain, rank: placeRank ? get(placeRank) : undefined })),
    summary: computed<HoldingsSummary>(() => summarizeSources(get(contributions), {
      liabilities: get(liabilities),
      liabilitiesExcluded: liabilitiesExcluded ? get(liabilitiesExcluded) : false,
      nfts: get(nfts),
    })),
  };
}
