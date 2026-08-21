import type { BigNumber } from '@rotki/common';
import type { ComputedRef } from 'vue';
import type { Balances } from '@/modules/accounts/blockchain-accounts';
import type { BlockchainTotal } from '@/modules/balances/blockchain-types';
import { isEmpty } from 'es-toolkit/compat';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { sortDesc } from '@/modules/core/common/data/bignumbers';

interface UseBlockchainTotalSummaryReturn { blockchainTotals: ComputedRef<BlockchainTotal[]> }

export function useBlockchainTotalSummary(): UseBlockchainTotalSummaryReturn {
  const { balances } = storeToRefs(useBalancesStore());
  const { isPricePending } = usePriceUtils();

  const blockchainTotals = computed<BlockchainTotal[]>(() => {
    const balanceData = get(balances);
    const sums: Record<string, BigNumber> = {};
    // A chain's card sums the values its assets carry, so one unpriced asset leaves the card short
    // by that asset's whole holding, with nothing to say so.
    const pending: Record<string, boolean> = {};

    const collectChain = (chain: string, chainBalance: Balances[string]): void => {
      for (const { assets } of Object.values(chainBalance)) {
        if (!assets || isEmpty(assets))
          continue;

        for (const [asset, protocol] of Object.entries(assets)) {
          pending[chain] = (pending[chain] ?? false) || isPricePending(asset);

          for (const { value } of Object.values(protocol))
            sums[chain] = sums[chain] ? sums[chain].plus(value) : value;
        }
      }
    };

    for (const chain in balanceData) {
      const chainBalance = balanceData[chain];
      if (chainBalance)
        collectChain(chain, chainBalance);
    }

    return Object.entries(sums)
      // A chain whose assets are all unpriced sums to zero, and dropping it would make the card
      // vanish and pop back in once prices land, rather than sit there loading.
      .filter(([chain, sum]) => sum.gt(0) || pending[chain])
      .sort(([, aValue], [, bValue]) => sortDesc(aValue, bValue))
      .map(([chain, value]) => ({
        chain,
        loading: pending[chain] ?? false,
        value,
      }) satisfies BlockchainTotal);
  });

  return {
    blockchainTotals,
  };
}
