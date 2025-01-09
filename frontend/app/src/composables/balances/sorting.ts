import { groupBy } from 'es-toolkit';
import { sortDesc, zeroBalance } from '@/utils/bignumbers';
import { balanceSum } from '@/utils/calculation';
import { useAssetCacheStore } from '@/store/assets/asset-cache';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import type { AssetBalance, AssetBalanceWithPrice, Balance, BigNumber } from '@rotki/common';
import type { AssetBalances } from '@/types/balances';
import type { ComputedRef } from 'vue';

interface UseBalanceSortingReturn {
  toSortedAssetBalanceArray: (
    ownedAssets: AssetBalances,
    isIgnored: (asset: string) => boolean,
    groupMultiChain?: boolean
  ) => AssetBalance[];
  toSortedAssetBalanceWithPrice: (
    ownedAssets: AssetBalances,
    isIgnored: (asset: string) => boolean,
    getPrice: (asset: string) => ComputedRef<BigNumber | null | undefined>,
    groupMultiChain?: boolean
  ) => AssetBalanceWithPrice[];
}

export function useBalanceSorting(): UseBalanceSortingReturn {
  const { assetInfo } = useAssetInfoRetrieval();
  const { fetchedAssetCollections } = storeToRefs(useAssetCacheStore());

  const toSortedAndGroupedArray = <T extends Balance>(
    ownedAssets: AssetBalances,
    isIgnored: (asset: string) => boolean,
    groupMultiChain: boolean,
    map: (asset: string) => T & { asset: string },
  ): T[] => {
    const data = Object.keys(ownedAssets)
      .filter(asset => !isIgnored(asset))
      .map(map);

    if (!groupMultiChain)
      return data.sort((a, b) => sortDesc(a.usdValue, b.usdValue));

    const groupedBalances = groupBy(data, (balance) => {
      const info = get(assetInfo(balance.asset));

      if (info?.collectionId)
        return `collection-${info.collectionId}`;

      return balance.asset;
    });

    const mapped: T[] = [];

    Object.keys(groupedBalances).forEach((key) => {
      const grouped = groupedBalances[key];
      const isAssetCollection = key.startsWith('collection-');
      const collectionKey = key.split('collection-')[1];
      const assetCollectionInfo = !isAssetCollection ? false : get(fetchedAssetCollections)?.[collectionKey];

      if (assetCollectionInfo && grouped.length > 1) {
        const sumBalance = grouped.reduce(
          (accumulator, currentBalance) => balanceSum(accumulator, currentBalance),
          zeroBalance(),
        );

        // If it contains a native asset, it should be used rather than the eip155 variant.
        // E.g., ETH should be prioritized over WETH, and BTC should be prioritized over cbBTC.
        let parentAsset = grouped[0];
        const nativeAsset = grouped.find(item => !isEvmIdentifier(item.asset));
        if (nativeAsset)
          parentAsset = nativeAsset;

        const parent: T = {
          ...parentAsset,
          ...sumBalance,
          breakdown: grouped,
        };

        mapped.push(parent);
      }
      else {
        mapped.push(...grouped);
      }
    });

    return mapped.sort((a, b) => sortDesc(a.usdValue, b.usdValue));
  };

  const toSortedAssetBalanceWithPrice = (
    ownedAssets: AssetBalances,
    isIgnored: (asset: string) => boolean,
    getPrice: (asset: string) => ComputedRef<BigNumber | null | undefined>,
    groupMultiChain = true,
  ): AssetBalanceWithPrice[] =>
    toSortedAndGroupedArray(ownedAssets, isIgnored, groupMultiChain, asset => ({
      amount: ownedAssets[asset].amount,
      asset,
      usdPrice: get(getPrice(asset)) ?? NoPrice,
      usdValue: ownedAssets[asset].usdValue,
    }));

  const toSortedAssetBalanceArray = (
    ownedAssets: AssetBalances,
    isIgnored: (asset: string) => boolean,
    groupMultiChain = false,
  ): AssetBalance[] =>
    toSortedAndGroupedArray(ownedAssets, isIgnored, groupMultiChain, asset => ({
      amount: ownedAssets[asset].amount,
      asset,
      usdValue: ownedAssets[asset].usdValue,
    }));

  return {
    toSortedAssetBalanceArray,
    toSortedAssetBalanceWithPrice,
  };
}
