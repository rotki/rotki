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
          for (const { usdValue } of Object.values(protocol)) {
            if (!sums[chain]) {
              sums[chain] = usdValue;
            }
            else {
              sums[chain] = sums[chain].plus(usdValue);
            }
          }
        }
      }
    }

    return Object.entries(sums)
      .filter(([, sum]) => sum.gt(0))
      .sort(([, aUsdValue], [, bUsdValue]) => sortDesc(aUsdValue, bUsdValue))
      .map(([chain, usdValue]) => ({
        chain,
        loading: false,
        usdValue,
      }) satisfies BlockchainTotal);
  });

  return {
    blockchainTotals,
  };
}
