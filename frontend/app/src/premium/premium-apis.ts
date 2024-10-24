import type {
  AssetBalanceWithPrice,
  AssetsApi,
  BalancerApi,
  BalancesApi,
  CompoundApi,
  LocationData,
  OwnedAssets,
  ProfitLossModel,
  StatisticsApi,
  SushiApi,
  TimedAssetBalances,
  TimedBalances,
  UserSettingsApi,
  UtilsApi,
} from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';

export function assetsApi(): AssetsApi {
  const { assetInfo, assetSymbol, assetName, tokenAddress } = useAssetInfoRetrieval();

  return {
    assetInfo,
    assetSymbol: (identifier: MaybeRef<string>) =>
      computed(() => {
        if (isNft(get(identifier)))
          return get(assetName(identifier));

        return get(assetSymbol(identifier));
      }),
    tokenAddress: (identifier: MaybeRef<string>) => tokenAddress(identifier),
  };
}

export function statisticsApi(): StatisticsApi {
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { fetchNetValue, getNetValue } = useStatisticsStore();
  const { queryLatestAssetValueDistribution, queryLatestLocationValueDistribution, queryTimedBalancesData }
    = useStatisticsApi();
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
    async timedBalances(asset: string, start: number, end: number, collectionId?: number): Promise<TimedBalances> {
      return queryTimedBalancesData(asset, start, end, collectionId);
    },
    async fetchNetValue(): Promise<void> {
      await fetchNetValue();
    },
    netValue: startingDate => getNetValue(startingDate),
  };
}

export function userSettings(): UserSettingsApi {
  const { privacyMode, scrambleData, shouldShowAmount, shouldShowPercentage, scrambleMultiplier }
    = storeToRefs(useSessionSettingsStore());
  const { floatingPrecision, currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { selectedTheme, dateInputFormat, graphZeroBased, showGraphRangeSelector }
    = storeToRefs(useFrontendSettingsStore());

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
    shouldShowPercentage,
  };
}

export function balancesApi(): BalancesApi {
  const { exchangeRate } = useBalancePricesStore();
  const { balancesByLocation } = useBalancesBreakdown();
  const { balances } = useAggregatedBalances();
  return {
    byLocation: balancesByLocation,
    balances: (groupMultiChain: boolean = false): ComputedRef<AssetBalanceWithPrice[]> =>
      // TODO update components
      useRefMap(balances(false, groupMultiChain), balances => balances.map(item => ({
        ...item,
        usdValue: item.value,
        breakdown: item.breakdown?.map(entry => ({
          ...entry,
          usdValue: entry.value,
        })),
      }))),
    exchangeRate: (currency: string) => computed(() => get(exchangeRate(currency)) ?? One),
  };
}

export function balancerApi(): BalancerApi {
  const store = useBalancerStore();
  const { pools, addresses } = storeToRefs(store);
  return {
    balancerProfitLoss: (addresses: string[]) => store.profitLoss(addresses),
    balancerBalances: (addresses: string[]) => store.balancerBalances(addresses),
    balancerPools: pools,
    balancerAddresses: addresses,
    fetchBalancerBalances: async (refresh: boolean) => store.fetchBalances(refresh),
  };
}

type ProfitLossRef = ComputedRef<ProfitLossModel[]>;

export function compoundApi(): CompoundApi {
  const { rewards, debtLoss, interestProfit, liquidationProfit } = storeToRefs(useCompoundStore());

  return {
    compoundRewards: rewards as ProfitLossRef,
    compoundDebtLoss: debtLoss as ProfitLossRef,
    compoundLiquidationProfit: liquidationProfit as ProfitLossRef,
    compoundInterestProfit: interestProfit as ProfitLossRef,
  };
}

export function sushiApi(): SushiApi {
  const store = useSushiswapStore();
  const { addresses, pools } = toRefs(store);

  const { balanceList, fetchBalances, fetchEvents, poolProfit } = store;

  return {
    addresses,
    pools,
    balances: balanceList,
    poolProfit,
    fetchEvents,
    fetchBalances,
  };
}

export function utilsApi(): UtilsApi {
  return {
    truncate: truncateAddress,
    getPoolName: useLiquidityPosition().getPoolName,
  };
}
