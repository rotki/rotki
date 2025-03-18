import type { AssetBalanceWithPrice } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useBalanceSorting } from '@/composables/balances/sorting';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useBlockchainStore } from '@/store/blockchain';
import { aggregateTotals } from '@/utils/blockchain/accounts';

interface UseBlockchainAggregatedBalancesReturn {
  useBlockchainAssets: (chains: MaybeRef<string[]>) => ComputedRef<AssetBalanceWithPrice[]>;
}

export function useBlockchainAggregatedBalances(): UseBlockchainAggregatedBalancesReturn {
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { assetAssociationMap } = useAssetInfoRetrieval();
  const { assetPrice } = useBalancePricesStore();
  const { toSortedAssetBalanceWithPrice } = useBalanceSorting();
  const { balances } = storeToRefs(useBlockchainStore());

  const blockchainAssets = (chains: MaybeRef<string[]> = []): ComputedRef<AssetBalanceWithPrice[]> => computed(() => {
    const blockchainAssets = aggregateTotals(get(balances), 'assets', {
      assetAssociationMap: get(assetAssociationMap),
      chains: get(chains),
      skipIdentifier: asset => isAssetIgnored(asset),
    });
    return toSortedAssetBalanceWithPrice(blockchainAssets, asset => isAssetIgnored(asset), assetPrice);
  });

  return {
    useBlockchainAssets: blockchainAssets,
  };
}
