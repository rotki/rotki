import { type AssetBalanceWithPrice, type BigNumber } from '@rotki/common';
import { type ProfitLossModel } from '@rotki/common/lib/defi';
import {
  type AssetsApi,
  type BalancerApi,
  type BalancesApi,
  type CompoundApi,
  type StatisticsApi,
  type SushiApi,
  type UserSettingsApi,
  type UtilsApi
} from '@rotki/common/lib/premium';
import {
  type LocationData,
  type OwnedAssets,
  type TimedAssetBalances,
  type TimedBalances
} from '@rotki/common/lib/statistics';
import { type MaybeRef } from '@vueuse/core';

export const assetsApi = (): AssetsApi => {
  const { assetInfo, assetSymbol, assetName, tokenAddress } =
    useAssetInfoRetrieval();

  return {
    assetInfo,
    assetSymbol: (identifier: MaybeRef<string>) =>
      computed(() => {
        if (isNft(get(identifier))) {
          return get(assetName(identifier));
        }
        return get(assetSymbol(identifier));
      }),
    tokenAddress: (identifier: MaybeRef<string>) => tokenAddress(identifier)
  };
};

export const statisticsApi = (): StatisticsApi => {
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { fetchNetValue, getNetValue } = useStatisticsStore();
  const {
    queryLatestAssetValueDistribution,
    queryLatestLocationValueDistribution,
    queryTimedBalancesData
  } = useStatisticsApi();
  const { queryOwnedAssets } = useAssetManagementApi();

  return {
    async assetValueDistribution(): Promise<TimedAssetBalances> {
      return queryLatestAssetValueDistribution();
    },
    async locationValueDistribution(): Promise<LocationData> {
      return queryLatestLocationValueDistribution();
    },
    async ownedAssets(): Promise<OwnedAssets> {
      const owned = await queryOwnedAssets();
      return owned.filter(asset => !get(isAssetIgnored(asset)));
    },
    async timedBalances(
      asset: string,
      start: number,
      end: number,
      collectionId?: number
    ): Promise<TimedBalances> {
      return queryTimedBalancesData(asset, start, end, collectionId);
    },
    async fetchNetValue(): Promise<void> {
      await fetchNetValue();
    },
    netValue: startingDate => getNetValue(startingDate)
  };
};

export const userSettings = (): UserSettingsApi => {
  const {
    privacyMode,
    scrambleData,
    shouldShowAmount,
    shouldShowPercentage,
    scrambleMultiplier
  } = storeToRefs(useSessionSettingsStore());
  const { floatingPrecision, currencySymbol } = storeToRefs(
    useGeneralSettingsStore()
  );
  const {
    selectedTheme,
    dateInputFormat,
    graphZeroBased,
    showGraphRangeSelector
  } = storeToRefs(useFrontendSettingsStore());

  return {
    floatingPrecision,
    currencySymbol,
    selectedTheme,
    dateInputFormat,
    graphZeroBased,
    showGraphRangeSelector,
    privacyMode,
    scrambleMultiplier,
    scrambleData,
    shouldShowAmount,
    shouldShowPercentage
  };
};

export const balancesApi = (): BalancesApi => {
  const { exchangeRate } = useBalancePricesStore();
  const { balancesByLocation } = useBalancesBreakdown();
  const { balances } = useAggregatedBalances();
  return {
    byLocation: balancesByLocation as ComputedRef<Record<string, BigNumber>>,
    // TODO: deprecate on the next major components version (it's only here for backwards compat)
    aggregatedBalances: balances(false, false) as ComputedRef<
      AssetBalanceWithPrice[]
    >,
    balances: (groupMultiChain = false) => balances(false, groupMultiChain),
    exchangeRate: (currency: string) =>
      computed(() => get(exchangeRate(currency)) ?? One)
  };
};

export const balancerApi = (): BalancerApi => {
  const store = useBalancerStore();
  const { pools, addresses } = storeToRefs(store);
  return {
    balancerProfitLoss: (addresses: string[]) => store.profitLoss(addresses),
    balancerBalances: (addresses: string[]) =>
      store.balancerBalances(addresses),
    balancerPools: pools,
    balancerAddresses: addresses,
    fetchBalancerBalances: async (refresh: boolean) =>
      await store.fetchBalances(refresh),
    fetchBalancerEvents: async (refresh: boolean) =>
      await store.fetchEvents(refresh)
  };
};

type ProfitLossRef = ComputedRef<ProfitLossModel[]>;

export const compoundApi = (): CompoundApi => {
  const { rewards, debtLoss, interestProfit, liquidationProfit } = storeToRefs(
    useCompoundStore()
  );

  return {
    compoundRewards: rewards as ProfitLossRef,
    compoundDebtLoss: debtLoss as ProfitLossRef,
    compoundLiquidationProfit: liquidationProfit as ProfitLossRef,
    compoundInterestProfit: interestProfit as ProfitLossRef
  };
};

export const sushiApi = (): SushiApi => {
  const store = useSushiswapStore();
  const { addresses, pools } = toRefs(store);

  const { balanceList, fetchBalances, fetchEvents, poolProfit } = store;

  return {
    addresses,
    pools,
    balances: balanceList,
    poolProfit,
    fetchEvents,
    fetchBalances
  };
};

export const utilsApi = (): UtilsApi => ({
  truncate: truncateAddress,
  getPoolName: useLiquidityPosition().getPoolName
});
