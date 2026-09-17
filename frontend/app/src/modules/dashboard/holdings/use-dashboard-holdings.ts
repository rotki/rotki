import type { ComputedRef } from 'vue';
import type { HoldingsSummary, LocationHolding } from '@/modules/dashboard/holdings/core/holdings-types';
import { mergeLocations } from '@/modules/dashboard/holdings/core/location-holdings';
import { summarizeSources } from '@/modules/dashboard/holdings/core/source-summary';
import { type HoldingsInputs, useHoldingsContributions } from '@/modules/dashboard/holdings/use-holdings-contributions';

interface UseDashboardHoldingsReturn {
  readonly summary: ComputedRef<HoldingsSummary>;
  readonly holdings: ComputedRef<LocationHolding[]>;
}

/** Net worth broken down by source kind and by place, for the dashboard. */
export function useDashboardHoldings(inputs: HoldingsInputs = useHoldingsContributions()): UseDashboardHoldingsReturn {
  const { contributions, liabilities, locationOfChain, nfts } = inputs;

  return {
    holdings: computed<LocationHolding[]>(() => mergeLocations(get(contributions), { locationOfChain })),
    summary: computed<HoldingsSummary>(() => summarizeSources(get(contributions), {
      liabilities: get(liabilities),
      nfts: get(nfts),
    })),
  };
}
