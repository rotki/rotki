import {
  type AssetBalance,
  type AssetBalanceWithPrice,
  type BigNumber
} from '@rotki/common';
import { type MaybeRef } from '@vueuse/core';
import { type AssetBalances } from '@/types/balances';

export const useBlockchainAggregatedBalances = () => {
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();
  const ethBalancesStore = useEthBalancesStore();
  const { totals: ethTotals, liabilities: ethLiabilities } =
    storeToRefs(ethBalancesStore);
  const { totals: btcTotals, liabilities: btcLiabilities } = storeToRefs(
    useBtcBalancesStore()
  );
  const { totals: chainTotals, liabilities: chainLiabilities } = storeToRefs(
    useChainBalancesStore()
  );
  const { assetPrice } = useBalancePricesStore();

  const totals: ComputedRef<AssetBalances> = computed(() => {
    const balances: AssetBalances = {};

    const totals = {
      ...get(ethTotals),
      ...get(btcTotals),
      ...get(chainTotals),
      LOOPRING: { ...get(ethBalancesStore.getLoopringAssetBalances()) }
    };

    for (const value of Object.values(totals)) {
      for (const asset of Object.keys(value)) {
        if (!balances[asset]) {
          balances[asset] = value[asset];
        } else {
          balances[asset] = balanceSum(balances[asset], value[asset]);
        }
      }
    }

    return balances;
  });

  const liabilities: ComputedRef<AssetBalances> = computed(() => {
    const balances: AssetBalances = {};
    const liabilities = {
      ...get(ethLiabilities),
      ...get(btcLiabilities),
      ...get(chainLiabilities)
    };

    for (const value of Object.values(liabilities)) {
      for (const asset of Object.keys(value)) {
        if (!balances[asset]) {
          balances[asset] = value[asset];
        } else {
          balances[asset] = balanceSum(balances[asset], value[asset]);
        }
      }
    }

    return balances;
  });

  const getTotals = (
    hideIgnored: MaybeRef<boolean> = ref(true)
  ): ComputedRef<AssetBalance[]> =>
    computed(() => {
      const ownedAssets = mergeAssociatedAssets(
        totals,
        getAssociatedAssetIdentifier
      );

      return toSortedAssetBalanceArray(
        get(ownedAssets),
        asset => hideIgnored && get(isAssetIgnored(asset))
      );
    });

  const blockchainTotal: ComputedRef<BigNumber> = computed(() =>
    bigNumberSum(get(getTotals()).map(asset => asset.usdValue))
  );

  const blockchainAssets: ComputedRef<AssetBalanceWithPrice[]> = computed(
    () => {
      const ownedAssets = mergeAssociatedAssets(
        totals,
        getAssociatedAssetIdentifier
      );
      return toSortedAssetBalanceWithPrice(
        get(ownedAssets),
        asset => get(isAssetIgnored(asset)),
        assetPrice
      );
    }
  );

  const locationBreakdown: ComputedRef<AssetBalances> = computed(() => {
    const assets: AssetBalances = {};
    for (const asset of get(getTotals())) {
      appendAssetBalance(asset, assets, getAssociatedAssetIdentifier);
    }

    return assets;
  });

  return {
    totals,
    liabilities,
    blockchainTotal,
    blockchainAssets,
    getTotals,
    locationBreakdown
  };
};
