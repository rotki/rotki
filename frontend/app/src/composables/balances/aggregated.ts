import type { AssetBalances } from '@/types/balances';
import type { AssetPriceInfo } from '@/types/prices';
import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useManualAssetBalances } from '@/composables/balances/manual';
import { useBalanceSorting } from '@/composables/balances/sorting';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useBlockchainStore } from '@/store/blockchain';
import { samePriceAssets } from '@/types/blockchain';
import { sumAssetBalances } from '@/utils/balances';
import { uniqueStrings } from '@/utils/data';
import { type AssetBalanceWithPrice, type ExclusionSource, Zero } from '@rotki/common';

interface UseAggregatedBalancesReturn {
  balances: (hideIgnored?: boolean, groupMultiChain?: boolean, exclude?: ExclusionSource[]) => ComputedRef<AssetBalanceWithPrice[]>;
  liabilities: (hideIgnored?: boolean) => ComputedRef<AssetBalanceWithPrice[]>;
  assetPriceInfo: (identifier: MaybeRef<string>, groupMultiChain?: MaybeRef<boolean>) => ComputedRef<AssetPriceInfo>;
  assets: (hideIgnored?: boolean) => ComputedRef<string[]>;
}

export function useAggregatedBalances(): UseAggregatedBalancesReturn {
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { assetPrice } = useBalancePricesStore();
  const { aggregatedLiabilities, aggregatedTotals } = storeToRefs(useBlockchainStore());
  const { balances: exchangeBalances } = storeToRefs(useExchangeBalancesStore());
  const { balances: manualBalances, liabilities: manualLiabilities } = useManualAssetBalances();

  const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();
  const { toSortedAssetBalanceWithPrice } = useBalanceSorting();

  const balances = (
    hideIgnored = true,
    groupMultiChain = true,
    exclude: ExclusionSource[] = [],
  ): ComputedRef<AssetBalanceWithPrice[]> =>
    computed<AssetBalanceWithPrice[]>(() => {
      const map = {
        blockchain: aggregatedTotals,
        exchange: exchangeBalances,
        manual: manualBalances,
      } as const;

      const sources: AssetBalances[] = Object.entries(map)
        .filter(([key]) => !exclude.includes(key as ExclusionSource))
        .map(([_key, value]) => get(value));

      const ownedAssets = sumAssetBalances(
        sources,
        getAssociatedAssetIdentifier,
      );

      return toSortedAssetBalanceWithPrice(
        ownedAssets,
        asset => hideIgnored && get(isAssetIgnored(asset)),
        assetPrice,
        groupMultiChain,
      );
    });

  const liabilities = (hideIgnored = true): ComputedRef<AssetBalanceWithPrice[]> =>
    computed<AssetBalanceWithPrice[]>(() => {
      const liabilities = sumAssetBalances(
        [get(aggregatedLiabilities), get(manualLiabilities)],
        getAssociatedAssetIdentifier,
      );

      return toSortedAssetBalanceWithPrice(
        liabilities,
        asset => hideIgnored && get(isAssetIgnored(asset)),
        assetPrice,
      );
    });

  const assets = (hideIgnored = true): ComputedRef<string[]> => computed<string[]>(() => {
    const additional: string[] = [];
    const liabilitiesAsset = get(liabilities(hideIgnored)).map(({ asset }) => {
      const samePrices = samePriceAssets[asset];
      if (samePrices)
        additional.push(...samePrices);

      return asset;
    });
    const assets = get(balances(hideIgnored, false)).map(({ asset }) => {
      const samePrices = samePriceAssets[asset];
      if (samePrices)
        additional.push(...samePrices);

      return asset;
    });

    assets.push(...liabilitiesAsset, ...additional);
    return assets.filter(uniqueStrings);
  });

  const assetPriceInfo = (
    identifier: MaybeRef<string>,
    groupMultiChain: MaybeRef<boolean> = ref(false),
  ): ComputedRef<AssetPriceInfo> => computed<AssetPriceInfo>(() => {
    const id = get(identifier);
    const assetValue = get(balances(true, get(groupMultiChain))).find(
      (value: AssetBalanceWithPrice) => value.asset === id,
    );

    return {
      amount: assetValue?.amount ?? Zero,
      usdPrice: assetValue?.usdPrice ?? Zero,
      usdValue: assetValue?.usdValue ?? Zero,
    };
  });

  return {
    assetPriceInfo,
    assets,
    balances,
    liabilities,
  };
}
