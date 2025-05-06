import type { AssetBalances } from '@/types/balances';
import type { ManualBalanceWithValue } from '@/types/manual-balances';
import type { AssetPriceInfo } from '@/types/prices';
import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useBalanceSorting } from '@/composables/balances/sorting';
import { useExchangeData } from '@/modules/balances/exchanges/use-exchange-data';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { samePriceAssets } from '@/types/blockchain';
import { sumAssetBalances } from '@/utils/balances';
import { aggregateTotals } from '@/utils/blockchain/accounts';
import { balanceSum } from '@/utils/calculation';
import { type AssetBalanceWithPrice, type Balance, type ExclusionSource, Zero } from '@rotki/common';

function toAssetBalances(balances: ManualBalanceWithValue[]): AssetBalances {
  const ownedAssets: AssetBalances = {};

  for (const { amount, asset, usdValue } of balances) {
    const balance: Balance = {
      amount,
      usdValue,
    };
    if (!ownedAssets[asset])
      ownedAssets[asset] = balance;
    else
      ownedAssets[asset] = balanceSum(ownedAssets[asset], balance);
  }
  return ownedAssets;
}

interface UseAggregatedBalancesReturn {
  balances: (hideIgnored?: boolean, groupMultiChain?: boolean, exclude?: ExclusionSource[]) => ComputedRef<AssetBalanceWithPrice[]>;
  liabilities: (hideIgnored?: boolean) => ComputedRef<AssetBalanceWithPrice[]>;
  assetPriceInfo: (identifier: MaybeRef<string>, groupMultiChain?: MaybeRef<boolean>) => ComputedRef<AssetPriceInfo>;
  assets: ComputedRef<string[]>;
}

export function useAggregatedBalances(): UseAggregatedBalancesReturn {
  const { useIsAssetIgnored } = useIgnoredAssetsStore();
  const { assetPrice } = usePriceUtils();
  const { balances: exchangeBalances } = useExchangeData();
  const { balances: blockchainBalances, manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());

  const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();
  const { toSortedAssetBalanceWithPrice } = useBalanceSorting();

  const balances = (
    hideIgnored = true,
    groupMultiChain = true,
    exclude: ExclusionSource[] = [],
  ): ComputedRef<AssetBalanceWithPrice[]> =>
    computed<AssetBalanceWithPrice[]>(() => {
      const map = {
        blockchain: aggregateTotals(get(blockchainBalances)),
        exchange: exchangeBalances,
        manual: toAssetBalances(get(manualBalances)),
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
        asset => hideIgnored && get(useIsAssetIgnored(asset)),
        assetPrice,
        groupMultiChain,
      );
    });

  const liabilities = (hideIgnored = true): ComputedRef<AssetBalanceWithPrice[]> =>
    computed<AssetBalanceWithPrice[]>(() => {
      const liabilities = sumAssetBalances(
        [
          aggregateTotals(get(blockchainBalances), 'liabilities'),
          toAssetBalances(get(manualLiabilities)),
        ],
        getAssociatedAssetIdentifier,
      );

      return toSortedAssetBalanceWithPrice(
        liabilities,
        asset => hideIgnored && get(useIsAssetIgnored(asset)),
        assetPrice,
      );
    });

  const assets = computed<string[]>(() => {
    const assetSet = new Set<string>();

    const processAsset = (asset: string): void => {
      assetSet.add(asset);
      const samePrices = samePriceAssets[asset];
      if (samePrices)
        samePrices.forEach(asset => assetSet.add(asset));
    };

    const processAssetBalances = (balances: AssetBalances): void => {
      Object.keys(balances).forEach(processAsset);
    };

    processAssetBalances(aggregateTotals(get(blockchainBalances)));
    processAssetBalances(aggregateTotals(get(blockchainBalances), 'liabilities'));
    processAssetBalances(get(exchangeBalances));

    get(manualBalances).forEach(({ asset }) => processAsset(asset));
    get(manualLiabilities).forEach(({ asset }) => processAsset(asset));

    return Array.from(assetSet);
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
