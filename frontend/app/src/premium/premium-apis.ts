import { isNft } from '@/utils/nft';
import { truncateAddress } from '@/utils/truncate';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useStatisticsStore } from '@/store/statistics';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useAggregatedBalances } from '@/composables/balances/aggregated';
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
  LocationData,
  OwnedAssets,
  StatisticsApi,
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

  const { fetchHistoricalAssetPrice, fetchNetValue, getNetValue } = useStatisticsStore();
  const { historicalDailyPriceStatus, historicalPriceStatus } = storeToRefs(useHistoricCachePriceStore());
  const {
    queryLatestAssetValueDistribution,
    queryLatestLocationValueDistribution,
    queryTimedBalancesData,
    queryTimedHistoricalBalancesData,
  } = useStatisticsApi();
  const { queryOwnedAssets } = useAssetManagementApi();

  const { cancelTaskByTaskType, isTaskRunning } = useTaskStore();

  return {
    async assetValueDistribution(): Promise<TimedAssetBalances> {
      return queryLatestAssetValueDistribution();
    },
    async cancelDailyHistoricPriceTask(): Promise<void> {
      await cancelTaskByTaskType(TaskType.FETCH_DAILY_HISTORIC_PRICE);
    },
    async cancelHistoricPriceTask(): Promise<void> {
      await cancelTaskByTaskType(TaskType.FETCH_HISTORIC_PRICE);
    },
    fetchNetValue,
    historicalDailyPriceStatus,
    historicalPriceStatus,
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
    assetPrice: (asset: string) => computed(() => get(assetPrice(asset)) ?? One),
    balances: (groupMultiChain = false, exclude = []) => balances(false, groupMultiChain, exclude),
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

export function utilsApi(): UtilsApi {
  return {
    truncate: truncateAddress,
  };
}
