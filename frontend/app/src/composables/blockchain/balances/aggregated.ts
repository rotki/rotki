import type { AssetBalanceWithPrice } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useBalanceSorting } from '@/composables/balances/sorting';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { aggregateTotals } from '@/utils/blockchain/accounts';

interface UseBlockchainAggregatedBalancesReturn {
  useBlockchainAssets: (chains: MaybeRef<string[]>) => ComputedRef<AssetBalanceWithPrice[]>;
}

export function useBlockchainAggregatedBalances(): UseBlockchainAggregatedBalancesReturn {
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { assetAssociationMap } = useAssetInfoRetrieval();
  const { assetPrice } = usePriceUtils();
  const { toSortedAssetBalanceWithPrice } = useBalanceSorting();
  const { balances } = storeToRefs(useBalancesStore());

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
