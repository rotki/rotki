import { type AssetBalance, type AssetBalanceWithPrice } from '@rotki/common';
import { type MaybeRef } from '@vueuse/core';
import { type ComputedRef } from 'vue';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useAggregatedBlockchainBalancesStore } from '@/store/blockchain/balances/aggregated';
import { samePriceAssets } from '@/types/blockchain';
import { type AssetPriceInfo } from '@/types/prices';
import {
  sumAssetBalances,
  toSortedAssetBalanceWithPrice
} from '@/utils/balances';
import { Zero } from '@/utils/bignumbers';
import { uniqueStrings } from '@/utils/data';

export const useAggregatedBalancesStore = defineStore(
  'balances/aggregated',
  () => {
    const { isAssetIgnored } = useIgnoredAssetsStore();
    const { assetPrice } = useBalancePricesStore();
    const { totals, liabilities: chainLiabilities } = storeToRefs(
      useAggregatedBlockchainBalancesStore()
    );
    const { balances: exchangeBalances } = storeToRefs(
      useExchangeBalancesStore()
    );
    const { balances: manualBalances, liabilities: manualLiabilities } =
      useManualAssetBalances();

    const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();

    const balances = (hideIgnored = true): ComputedRef<AssetBalance[]> =>
      computed(() => {
        const ownedAssets = sumAssetBalances(
          [get(totals), get(exchangeBalances), get(manualBalances)],
          getAssociatedAssetIdentifier
        );

        return toSortedAssetBalanceWithPrice(
          ownedAssets,
          asset => hideIgnored && get(isAssetIgnored(asset)),
          assetPrice
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
            if (samePrices) additional.push(...samePrices);
            return asset;
          }
        );
        const assets = get(balances(hideIgnored)).map(({ asset }) => {
          const samePrices = samePriceAssets[asset];
          if (samePrices) additional.push(...samePrices);
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
      identifier: MaybeRef<string>
    ): ComputedRef<AssetPriceInfo> => {
      return computed(() => {
        const id = get(identifier);
        const assetValue = (get(balances()) as AssetBalanceWithPrice[]).find(
          (value: AssetBalanceWithPrice) => value.asset === id
        );
        return {
          usdPrice: assetValue?.usdPrice ?? Zero,
          amount: assetValue?.amount ?? Zero,
          usdValue: assetValue?.usdValue ?? Zero
        };
      });
    };

    return {
      balances,
      liabilities,
      assetPriceInfo,
      assets
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useAggregatedBalancesStore, import.meta.hot)
  );
}
