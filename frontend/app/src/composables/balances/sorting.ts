import type { AssetBalances } from '@/types/balances';
import type { ComputedRef } from 'vue';
import { useCollectionInfo } from '@/modules/assets/use-collection-info';
import { sortDesc, zeroBalance } from '@/utils/bignumbers';
import { balanceSum } from '@/utils/calculation';
import { type AssetBalanceWithPrice, type Balance, type BigNumber, NoPrice } from '@rotki/common';
import { groupBy } from 'es-toolkit';

interface UseBalanceSortingReturn {
  toSortedAssetBalanceWithPrice: (
    ownedAssets: AssetBalances,
    isIgnored: (asset: string) => boolean,
    getPrice: (asset: string) => ComputedRef<BigNumber | null | undefined>,
    groupMultiChain?: boolean
  ) => AssetBalanceWithPrice[];
}

export function useBalanceSorting(): UseBalanceSortingReturn {
  const { useCollectionId, useCollectionMainAsset } = useCollectionInfo();

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
      const collectionId = get(useCollectionId(balance.asset));

      if (collectionId)
        return `collection-${collectionId}`;

      return balance.asset;
    });

    const mapped: T[] = [];

    Object.keys(groupedBalances).forEach((key) => {
      const grouped = groupedBalances[key];
      const isAssetCollection = key.startsWith('collection-');
      const collectionKey = key.split('collection-')[1];
      const mainAsset = !isAssetCollection ? false : get(useCollectionMainAsset(collectionKey));

      if (mainAsset) {
        const sumBalance = grouped.reduce(
          (accumulator, currentBalance) => balanceSum(accumulator, currentBalance),
          zeroBalance(),
        );

        const parent: T = {
          ...grouped[0],
          ...sumBalance,
          asset: mainAsset,
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

  return {
    toSortedAssetBalanceWithPrice,
  };
}
