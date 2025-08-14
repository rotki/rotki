import type { MaybeRef } from '@vueuse/core';
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
import { useAssetManagementApi } from '@/composables/api/assets/management';
import { usePriceApi } from '@/composables/api/balances/price';
import { useStatisticsApi } from '@/composables/api/statistics/statistics-api';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatisticsStore } from '@/store/statistics';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { isNft } from '@/utils/nft';
import { truncateAddress } from '@/utils/truncate';

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
  const { useIsAssetIgnored } = useIgnoredAssetsStore();

  const { fetchHistoricalAssetPrice, fetchNetValue, getNetValue } = useStatisticsStore();
  const { failedDailyPrices, historicalDailyPriceStatus } = storeToRefs(useHistoricCachePriceStore());
  const {
    queryLatestAssetValueDistribution,
    queryLatestLocationValueDistribution,
    queryTimedBalancesData,
    queryTimedHistoricalBalancesData,
  } = useStatisticsApi();
  const { queryOwnedAssets } = useAssetManagementApi();

  const { cancelTaskByTaskType, useIsTaskRunning } = useTaskStore();

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
    netValue: startingDate => getNetValue(startingDate),
    async ownedAssets(): Promise<OwnedAssets> {
      const owned = await queryOwnedAssets();
      return owned.filter(asset => !get(useIsAssetIgnored(asset)));
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
    scrambleMultiplier: scrambleMultiplierRef,
    selectedTheme,
    shouldShowAmount,
    shouldShowPercentage,
    showGraphRangeSelector,
    subscriptDecimals,
    thousandSeparator,
    useHistoricalAssetBalances,
  } = storeToRefs(useFrontendSettingsStore());
  const { currencySymbol, floatingPrecision } = storeToRefs(useGeneralSettingsStore());

  const scrambleMultiplier = ref<number>(get(scrambleMultiplierRef) ?? 1);

  watchEffect(() => {
    const newValue = get(scrambleMultiplierRef);
    if (newValue !== undefined)
      set(scrambleMultiplier, newValue);
  });

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
  const { assetPriceInCurrentCurrency, useExchangeRate } = usePriceUtils();
  const { balances, balancesByLocation } = useAggregatedBalances();
  const { createKey, isPending } = useHistoricCachePriceStore();
  const { queryOnlyCacheHistoricalRates } = usePriceApi();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

  return {
    assetPrice: (asset: string) => computed(() => get(assetPriceInCurrentCurrency(asset)) ?? One),
    balances: (groupMultiChain = false, exclude = []) => balances(false, groupMultiChain, exclude),
    byLocation: balancesByLocation,
    exchangeRate: (currency: string) => computed(() => get(useExchangeRate(currency)) ?? One),
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
