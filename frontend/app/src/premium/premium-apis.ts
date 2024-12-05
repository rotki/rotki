import { isNft } from '@/utils/nft';
import { truncateAddress } from '@/utils/truncate';
import { useSushiswapStore } from '@/store/defi/sushiswap';
import { useCompoundStore } from '@/store/defi/compound';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useStatisticsStore } from '@/store/statistics';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import type {
  AssetsApi,
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
  const { assetInfo, assetName, assetSymbol, tokenAddress } = useAssetInfoRetrieval();

  return {
    assetInfo,
    assetSymbol: (identifier: MaybeRef<string>) => computed(() => {
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
  const {
    queryLatestAssetValueDistribution,
    queryLatestLocationValueDistribution,
    queryTimedBalancesData,
  } = useStatisticsApi();
  const { queryOwnedAssets } = useAssetManagementApi();

  return {
    async assetValueDistribution(): Promise<TimedAssetBalances> {
      return queryLatestAssetValueDistribution();
    },
    async fetchNetValue(): Promise<void> {
      await fetchNetValue();
    },
    async locationValueDistribution(): Promise<LocationData> {
      return queryLatestLocationValueDistribution();
    },
    netValue: startingDate => getNetValue(startingDate),
    async ownedAssets(): Promise<OwnedAssets> {
      const owned = await queryOwnedAssets();
      return owned.filter(asset => !get(isAssetIgnored(asset)));
    },
    async timedBalances(asset: string, start: number, end: number, collectionId?: number): Promise<TimedBalances> {
      return queryTimedBalancesData(asset, start, end, collectionId);
    },
  };
}

export function userSettings(): UserSettingsApi {
  const {
    privacyMode,
    scrambleData,
    scrambleMultiplier,
    shouldShowAmount,
    shouldShowPercentage,
  } = storeToRefs(useSessionSettingsStore());
  const {
    dateInputFormat,
    graphZeroBased,
    selectedTheme,
    showGraphRangeSelector,
  } = storeToRefs(useFrontendSettingsStore());
  const { currencySymbol, floatingPrecision } = storeToRefs(useGeneralSettingsStore());

  return {
    currencySymbol,
    dateInputFormat,
    floatingPrecision,
    graphZeroBased,
    privacyMode,
    scrambleData,
    scrambleMultiplier,
    selectedTheme,
    shouldShowAmount,
    shouldShowPercentage,
    showGraphRangeSelector,
  };
}

export function balancesApi(): BalancesApi {
  const { exchangeRate } = useBalancePricesStore();
  const { balancesByLocation } = useBalancesBreakdown();
  const { balances } = useAggregatedBalances();
  return {
    // TODO: deprecate on the next major components version (it's only here for backwards compat)
    aggregatedBalances: balances(false, false),
    balances: (groupMultiChain = false) => balances(false, groupMultiChain),
    byLocation: balancesByLocation,
    exchangeRate: (currency: string) => computed(() => get(exchangeRate(currency)) ?? One),
  };
}

type ProfitLossRef = ComputedRef<ProfitLossModel[]>;

export function compoundApi(): CompoundApi {
  const { debtLoss, interestProfit, liquidationProfit, rewards } = storeToRefs(useCompoundStore());

  return {
    compoundDebtLoss: debtLoss as ProfitLossRef,
    compoundInterestProfit: interestProfit as ProfitLossRef,
    compoundLiquidationProfit: liquidationProfit as ProfitLossRef,
    compoundRewards: rewards as ProfitLossRef,
  };
}

export function sushiApi(): SushiApi {
  const store = useSushiswapStore();
  const { addresses, pools } = toRefs(store);

  const { balanceList, fetchBalances, fetchEvents, poolProfit } = store;

  return {
    addresses,
    balances: balanceList,
    fetchBalances,
    fetchEvents,
    poolProfit,
    pools,
  };
}

export function utilsApi(): UtilsApi {
  return {
    getPoolName: useLiquidityPosition().getPoolName,
    truncate: truncateAddress,
  };
}
