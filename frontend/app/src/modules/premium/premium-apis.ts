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
import { useSetting } from '@/modules/settings/use-setting';
import { useStatisticsApi } from '@/modules/statistics/api/use-statistics-api';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';
import { ActivityKind, ActivityPart, useNativeTask } from '@/modules/task-center/use-native-task';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

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

  const { cancelByPrefix } = useNativeTask();
  const { useIsActivePrefix } = useTaskCenter();

  return {
    async assetValueDistribution(): Promise<TimedAssetBalances> {
      return queryLatestAssetValueDistribution();
    },
    // Both stay `async` — they are part of the premium bundle's external StatisticsApi contract.
    async cancelDailyHistoricPriceTask(): Promise<void> {
      cancelByPrefix(ActivityKind.PRICES, ActivityPart.DAILY);
    },
    async cancelHistoricPriceTask(): Promise<void> {
      cancelByPrefix(ActivityKind.PRICES, ActivityPart.HISTORIC);
    },
    failedDailyPrices,
    fetchNetValue,
    historicalDailyPriceStatus,
    isQueryingDailyPrices: useIsActivePrefix(ActivityKind.PRICES, ActivityPart.DAILY),
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
  return {
    currencySymbol: useSetting('currencySymbol'),
    dateInputFormat: useSetting('dateInputFormat'),
    decimalSeparator: useSetting('decimalSeparator'),
    floatingPrecision: useSetting('floatingPrecision'),
    graphZeroBased: useSetting('graphZeroBased'),
    privacyMode: useSetting('privacyMode'),
    scrambleData: useSetting('scrambleData'),
    scrambleMultiplier: useSetting('scrambleMultiplier'),
    selectedTheme: useSetting('selectedTheme'),
    shouldShowAmount: useSetting('shouldShowAmount'),
    shouldShowPercentage: useSetting('shouldShowPercentage'),
    showGraphRangeSelector: useSetting('showGraphRangeSelector'),
    subscriptDecimals: useSetting('subscriptDecimals'),
    thousandSeparator: useSetting('thousandSeparator'),
    useHistoricalAssetBalances: useSetting('useHistoricalAssetBalances'),
  };
}

export function balancesApi(): BalancesApi {
  const { getAssetPrice, getExchangeRate } = usePriceUtils();
  const { balancesByLocation, useBalances } = useAggregatedBalances();
  const { queryOnlyCacheHistoricalRates } = usePriceApi();
  const currencySymbol = useSetting('currencySymbol');

  return {
    assetPrice: (asset: string) => computed(() => getAssetPrice(asset, One)),
    balances: (groupMultiChain = false, exclude = []) => useBalances(false, groupMultiChain, exclude),
    byLocation: balancesByLocation,
    exchangeRate: (currency: string) => computed(() => getExchangeRate(currency, One)),
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
