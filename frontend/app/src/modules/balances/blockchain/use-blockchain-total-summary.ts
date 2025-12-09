import type { BigNumber } from '@rotki/common';
import type { ComputedRef } from 'vue';
import type { BlockchainTotal } from '@/types/blockchain';
import { isEmpty } from 'es-toolkit/compat';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { sortDesc } from '@/utils/bignumbers';

interface UseBlockchainTotalsSummaryReturn { blockchainTotals: ComputedRef<BlockchainTotal[]> }

export function useBlockchainTotalSummary(): UseBlockchainTotalsSummaryReturn {
  const { balances } = storeToRefs(useBalancesStore());

  const blockchainTotals = computed<BlockchainTotal[]>(() => {
    const balanceData = get(balances);
    const sums: Record<string, BigNumber> = {};

    for (const chain in balanceData) {
      const chainBalance = balanceData[chain];
      if (!chainBalance)
        continue;

      for (const { assets } of Object.values(chainBalance)) {
        if (!assets || isEmpty(assets))
          continue;

        for (const protocol of Object.values(assets)) {
          for (const { value } of Object.values(protocol)) {
            if (!sums[chain]) {
              sums[chain] = value;
            }
            else {
              sums[chain] = sums[chain].plus(value);
            }
          }
        }
      }
    }

    return Object.entries(sums)
      .filter(([, sum]) => sum.gt(0))
      .sort(([, aValue], [, bValue]) => sortDesc(aValue, bValue))
      .map(([chain, value]) => ({
        chain,
        loading: false,
        value,
      }) satisfies BlockchainTotal);
  });

  return {
    blockchainTotals,
  };
}
