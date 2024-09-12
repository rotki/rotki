import type { AssetBalance, AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import type { AssetBalances } from '@/types/balances';

interface UseBlockchainAggregatedBalancesReturn {
  blockchainTotal: ComputedRef<BigNumber>;
  blockchainAssets: ComputedRef<AssetBalanceWithPrice[]>;
  locationBreakdown: ComputedRef<AssetBalances>;
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

  const blockchainTotal = computed<BigNumber>(() => bigNumberSum(getTotals().map(asset => asset.usdValue)));

  const blockchainAssets = computed<AssetBalanceWithPrice[]>(() => {
    const ownedAssets = mergeAssociatedAssets(aggregatedTotals, getAssociatedAssetIdentifier);
    return toSortedAssetBalanceWithPrice(get(ownedAssets), asset => get(isAssetIgnored(asset)), assetPrice);
  });

  const locationBreakdown = computed<AssetBalances>(() => {
    const assets: AssetBalances = {};
    for (const asset of getTotals()) appendAssetBalance(asset, assets, getAssociatedAssetIdentifier);

    return assets;
  });

  return {
    blockchainTotal,
    blockchainAssets,
    locationBreakdown,
  };
}
