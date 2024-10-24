import type { BigNumber } from '@rotki/common';
import type { AssetBalance, AssetBalanceWithPrice } from '@/types/balances';
import type { ComputedRef } from 'vue';

interface UseBlockchainAggregatedBalancesReturn {
  blockchainTotal: ComputedRef<BigNumber>;
  blockchainAssets: ComputedRef<AssetBalanceWithPrice[]>;
  locationBreakdown: ComputedRef<Record<string, AssetBalance>>;
}

export function useBlockchainAggregatedBalances(): UseBlockchainAggregatedBalancesReturn {
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();
  const { assetPrice } = useBalancePricesStore();
  const { toSortedAssetBalanceWithPrice, toSortedAssetBalanceArray } = useBalanceSorting();
  const { aggregatedTotals } = storeToRefs(useBlockchainStore());

  const getTotals = (): AssetBalance[] => {
    const ownedAssets = mergeAssociatedAssets(aggregatedTotals, getAssociatedAssetIdentifier);

    return toSortedAssetBalanceArray(get(ownedAssets), asset => get(isAssetIgnored(asset)));
  };

  const blockchainTotal = computed<BigNumber>(() => bigNumberSum(getTotals().map(asset => asset.value)));

  const blockchainAssets = computed<AssetBalanceWithPrice[]>(() => {
    const ownedAssets = mergeAssociatedAssets(aggregatedTotals, getAssociatedAssetIdentifier);
    return toSortedAssetBalanceWithPrice(get(ownedAssets), asset => get(isAssetIgnored(asset)), assetPrice);
  });

  const locationBreakdown = computed<Record<string, AssetBalance>>(() => {
    const assets: Record<string, AssetBalance> = {};
    for (const asset of getTotals())
      appendAssetBalance(asset, assets, getAssociatedAssetIdentifier);

    return assets;
  });

  return {
    blockchainTotal,
    blockchainAssets,
    locationBreakdown,
  };
}
