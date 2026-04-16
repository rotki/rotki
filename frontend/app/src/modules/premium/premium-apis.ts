import type { MaybeRef } from 'vue';
import {
  type AssetsApi,
  type BalancesApi,
  type BigNumber,
  type LocationData,
  One,
  type OwnedAssets,
  type StatisticsApi,
  type TimedAssetBalances,
  type TimedAssetHistoricalBalances,
  type TimedBalances,
  type UserSettingsApi,
  type UtilsApi,
} from '@rotki/common';
import { useAssetManagementApi } from '@/modules/assets/api/use-asset-management-api';
import { isNft } from '@/modules/assets/nft-utils';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { useHistoricalPriceFetcher } from '@/modules/assets/prices/use-historical-price-fetcher';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { usePriceApi } from '@/modules/balances/api/use-price-api';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import { useStatisticsApi } from '@/modules/statistics/api/use-statistics-api';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

export function assetsApi(): AssetsApi {
  const { getAssetInfo, useAssetInfo, useTokenAddress } = useAssetInfoRetrieval();

  return {
    assetInfo: useAssetInfo,
    assetSymbol: (identifier: MaybeRef<string>) => computed<string>(() => {
      if (isNft(get(identifier)))
        return getAssetInfo(get(identifier))?.name ?? '';

      return getAssetInfo(get(identifier))?.symbol ?? '';
    }),
    tokenAddress: (identifier: MaybeRef<string>) => useTokenAddress(identifier),
  };
}

export function statisticsApi(): StatisticsApi {
  const { isAssetIgnored } = useAssetsStore();

  const { useNetValue } = useStatisticsStore();
  const { fetchNetValue } = useStatisticsDataFetching();
  const { fetchHistoricalAssetPrice } = useHistoricalPriceFetcher();
  const { failedDailyPrices, historicalDailyPriceStatus } = useHistoricPriceCache();
  const {
    queryLatestAssetValueDistribution,
    queryLatestLocationValueDistribution,
    queryTimedBalancesData,
    queryTimedHistoricalBalancesData,
  } = useStatisticsApi();
  const { queryOwnedAssets } = useAssetManagementApi();

  const { cancelTaskByTaskType } = useTaskHandler();
  const { useIsTaskRunning } = useTaskStore();

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
    failedDailyPrices,
    fetchNetValue,
    historicalDailyPriceStatus,
    isQueryingDailyPrices: useIsTaskRunning(TaskType.FETCH_DAILY_HISTORIC_PRICE),
    async locationValueDistribution(): Promise<LocationData> {
      return queryLatestLocationValueDistribution();
    },
    netValue: startingDate => useNetValue(startingDate),
    async ownedAssets(): Promise<OwnedAssets> {
      const owned = await queryOwnedAssets();
      return owned.filter(asset => !isAssetIgnored(asset));
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
    dateInputFormat,
    decimalSeparator,
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
  const { getAssetPrice, getExchangeRate } = usePriceUtils();
  const { balancesByLocation, useBalances } = useAggregatedBalances();
  const { createKey, isPending } = useHistoricPriceCache();
  const { queryOnlyCacheHistoricalRates } = usePriceApi();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

  return {
    assetPrice: (asset: string) => computed(() => getAssetPrice(asset, One)),
    balances: (groupMultiChain = false, exclude = []) => useBalances(false, groupMultiChain, exclude),
    byLocation: balancesByLocation,
    exchangeRate: (currency: string) => computed(() => getExchangeRate(currency, One)),
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
