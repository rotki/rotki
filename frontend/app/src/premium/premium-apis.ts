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
import { useAggregatedBalances } from '@/composables/balances/aggregated';
import { useLiquidityPosition } from '@/composables/defi';
import { useBalancesBreakdown } from '@/composables/balances/breakdown';
import { useAssetManagementApi } from '@/composables/api/assets/management';
import { useStatisticsApi } from '@/composables/api/statistics/statistics-api';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
import { usePriceApi } from '@/composables/api/balances/price';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import type {
  AssetsApi,
  BalancesApi,
  BigNumber,
  CompoundApi,
  LocationData,
  OwnedAssets,
  ProfitLossModel,
  StatisticsApi,
  SushiApi,
  TimedAssetBalances,
  TimedAssetHistoricalBalances,
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
  const statisticsStore = useStatisticsStore();

  const { fetchHistoricalAssetPrice, fetchNetValue, getNetValue } = statisticsStore;
  const { historicalAssetPriceStatus } = storeToRefs(statisticsStore);
  const {
    queryLatestAssetValueDistribution,
    queryLatestLocationValueDistribution,
    queryTimedBalancesData,
    queryTimedHistoricalBalancesData,
  } = useStatisticsApi();
  const { queryOwnedAssets } = useAssetManagementApi();

  const { isTaskRunning } = useTaskStore();

  return {
    async assetValueDistribution(): Promise<TimedAssetBalances> {
      return queryLatestAssetValueDistribution();
    },
    async fetchNetValue(): Promise<void> {
      await fetchNetValue();
    },
    historicalAssetPriceStatus,
    isQueryingDailyPrices: isTaskRunning(TaskType.FETCH_DAILY_HISTORIC_PRICE),
    async locationValueDistribution(): Promise<LocationData> {
      return queryLatestLocationValueDistribution();
    },
    netValue: startingDate => getNetValue(startingDate),
    async ownedAssets(): Promise<OwnedAssets> {
      const owned = await queryOwnedAssets();
      return owned.filter(asset => !get(isAssetIgnored(asset)));
    },
    queryHistoricalAssetPrices: fetchHistoricalAssetPrice,
    async timedBalances(asset: string, start: number, end: number, collectionId?: number): Promise<TimedBalances> {
      return queryTimedBalancesData(asset, start, end, collectionId);
    },
    async timedHistoricalBalances(asset: string, start: number, end: number, collectionId?: number): Promise<TimedAssetHistoricalBalances> {
      return queryTimedHistoricalBalancesData(asset, start, end, collectionId);
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
    decimalSeparator,
    graphZeroBased,
    selectedTheme,
    showGraphRangeSelector,
    subscriptDecimals,
    thousandSeparator,
    useHistoricalAssetBalances,
  } = storeToRefs(useFrontendSettingsStore());
  const { currencySymbol, floatingPrecision } = storeToRefs(useGeneralSettingsStore());

  return {
    currencySymbol,
    dateInputFormat,
    decimalSeparator,
    floatingPrecision,
    graphZeroBased,
    privacyMode,
    scrambleData,
    scrambleMultiplier,
    selectedTheme,
    shouldShowAmount,
    shouldShowPercentage,
    showGraphRangeSelector,
    subscriptDecimals,
    thousandSeparator,
    useHistoricalAssetBalances,
  };
}

export function balancesApi(): BalancesApi {
  const { assetPrice, exchangeRate } = useBalancePricesStore();
  const { balancesByLocation } = useBalancesBreakdown();
  const { balances } = useAggregatedBalances();
  const { createKey, historicPriceInCurrentCurrency, isPending } = useHistoricCachePriceStore();
  const { queryOnlyCacheHistoricalRates } = usePriceApi();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

  return {
    // TODO: deprecate on the next major components version (it's only here for backwards compat)
    aggregatedBalances: balances(false, false),
    assetPrice: (asset: string) => computed(() => get(assetPrice(asset)) ?? One),
    balances: (groupMultiChain = false) => balances(false, groupMultiChain),
    byLocation: balancesByLocation,
    exchangeRate: (currency: string) => computed(() => get(exchangeRate(currency)) ?? One),
    historicPriceInCurrentCurrency,
    isHistoricPricePending: (asset: string, timestamp: number) => isPending(createKey(asset, timestamp)),
    queryOnlyCacheHistoricalRates: async (asset: string, timestamp: number[]): Promise<Record<string, BigNumber>> => {
      const data = await queryOnlyCacheHistoricalRates({
        assetsTimestamp: timestamp.map(item => [asset, item.toString()]),
        onlyCachePeriod: 3600 * 24,
        targetAsset: get(currencySymbol),
      });

      return data.assets[asset] ?? {};
    },
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
