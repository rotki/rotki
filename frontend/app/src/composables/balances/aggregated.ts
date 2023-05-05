import { type AssetBalanceWithPrice } from '@rotki/common';
import { type MaybeRef } from '@vueuse/core';
import { type ComputedRef } from 'vue';
import { samePriceAssets } from '@/types/blockchain';
import { type AssetPriceInfo } from '@/types/prices';

export const useAggregatedBalances = () => {
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { assetPrice } = useBalancePricesStore();
  const { totals, liabilities: chainLiabilities } =
    useBlockchainAggregatedBalances();
  const { balances: exchangeBalances } = storeToRefs(
    useExchangeBalancesStore()
  );
  const { balances: manualBalances, liabilities: manualLiabilities } =
    useManualAssetBalances();

  const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();

  const balances = (
    hideIgnored = true,
    groupMultiChain = true
  ): ComputedRef<AssetBalanceWithPrice[]> =>
    computed(() => {
      const ownedAssets = sumAssetBalances(
        [get(totals), get(exchangeBalances), get(manualBalances)],
        getAssociatedAssetIdentifier
      );

      return toSortedAssetBalanceWithPrice(
        ownedAssets,
        asset => hideIgnored && get(isAssetIgnored(asset)),
        assetPrice,
        groupMultiChain
      );
    });

  const liabilities = (
    hideIgnored = true
  ): ComputedRef<AssetBalanceWithPrice[]> =>
    computed(() => {
      const liabilities = sumAssetBalances(
        [get(chainLiabilities), get(manualLiabilities)],
        getAssociatedAssetIdentifier
      );

      return toSortedAssetBalanceWithPrice(
        liabilities,
        asset => hideIgnored && get(isAssetIgnored(asset)),
        assetPrice
      );
    });

  const assets = (hideIgnored = true): ComputedRef<string[]> =>
    computed(() => {
      const additional: string[] = [];
      const liabilitiesAsset = get(liabilities(hideIgnored)).map(
        ({ asset }) => {
          const samePrices = samePriceAssets[asset];
          if (samePrices) {
            additional.push(...samePrices);
          }
          return asset;
        }
      );
      const assets = get(balances(hideIgnored)).map(({ asset }) => {
        const samePrices = samePriceAssets[asset];
        if (samePrices) {
          additional.push(...samePrices);
        }
        return asset;
      });

      const { lpAggregatedBalances } = useLiquidityPosition();
      const lpBalances = get(lpAggregatedBalances(false));
      const lpAssets = lpBalances
        .map(item => item.asset)
        .filter(item => !!item) as string[];

      assets.push(...liabilitiesAsset, ...lpAssets, ...additional);
      return assets.filter(uniqueStrings);
    });

  const assetPriceInfo = (
    identifier: MaybeRef<string>,
    groupMultiChain: MaybeRef<boolean> = ref(false)
  ): ComputedRef<AssetPriceInfo> =>
    computed(() => {
      const id = get(identifier);
      const assetValue = get(balances(true, get(groupMultiChain))).find(
        (value: AssetBalanceWithPrice) => value.asset === id
      );

      return {
        usdPrice: assetValue?.usdPrice ?? Zero,
        amount: assetValue?.amount ?? Zero,
        usdValue: assetValue?.usdValue ?? Zero
      };
    });

  return {
    balances,
    liabilities,
    assetPriceInfo,
    assets
  };
};
