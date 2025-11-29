import {
  type HistoricalAssetPricePayload,
  LocationData,
  NetValue,
  TimedAssetBalances,
  TimedAssetHistoricalBalances,
  TimedBalances,
} from '@rotki/common';
import { api } from '@/modules/api/rotki-api';
import { type PendingTask, PendingTaskSchema } from '@/types/task';

interface UseStatisticsApiReturn {
  queryNetValueData: (includeNfts: boolean) => Promise<NetValue>;
  queryTimedBalancesData: (asset: string, fromTimestamp: number, toTimestamp: number, collectionId?: number) => Promise<TimedBalances>;
  queryTimedHistoricalBalancesData: (asset: string, fromTimestamp: number, toTimestamp: number, collectionId?: number) => Promise<TimedAssetHistoricalBalances>;
  queryLatestLocationValueDistribution: () => Promise<LocationData>;
  queryLatestAssetValueDistribution: () => Promise<TimedAssetBalances>;
  queryStatisticsRenderer: () => Promise<string>;
  queryHistoricalAssetPrices: (payload: HistoricalAssetPricePayload) => Promise<PendingTask>;
}

export function useStatisticsApi(): UseStatisticsApiReturn {
  const queryNetValueData = async (includeNfts: boolean): Promise<NetValue> => {
    const response = await api.get<NetValue>('/statistics/netvalue', {
      query: { includeNfts },
    });

    return NetValue.parse(response);
  };

  const queryTimedBalancesData = async (
    asset: string,
    fromTimestamp: number,
    toTimestamp: number,
    collectionId?: number,
  ): Promise<TimedBalances> => {
    const payload = {
      fromTimestamp,
      toTimestamp,
      ...(isDefined(collectionId) ? { collectionId } : { asset }),
    };
    const response = await api.post<TimedBalances>('/statistics/balance', payload);

    return TimedBalances.parse(response);
  };

  const queryTimedHistoricalBalancesData = async (
    asset: string,
    fromTimestamp: number,
    toTimestamp: number,
    collectionId?: number,
  ): Promise<TimedAssetHistoricalBalances> => {
    const payload = {
      fromTimestamp,
      toTimestamp,
      ...(isDefined(collectionId) ? { collectionId } : { asset }),
    };
    const response = await api.post<TimedAssetHistoricalBalances>('/balances/historical/asset', payload);

    return TimedAssetHistoricalBalances.parse(response);
  };

  const queryLatestLocationValueDistribution = async (): Promise<LocationData> => {
    const response = await api.get<LocationData>('/statistics/value_distribution', {
      query: { distributionBy: 'location' },
    });
    return LocationData.parse(response);
  };

  const queryLatestAssetValueDistribution = async (): Promise<TimedAssetBalances> => {
    const response = await api.get<TimedAssetBalances>('/statistics/value_distribution', {
      query: { distributionBy: 'asset' },
    });
    return TimedAssetBalances.parse(response);
  };

  const queryStatisticsRenderer = async (): Promise<string> => api.get<string>('/statistics/renderer');

  const queryHistoricalAssetPrices = async (payload: HistoricalAssetPricePayload): Promise<PendingTask> => {
    const response = await api.post<PendingTask>('/balances/historical/asset/prices', {
      ...payload,
      asyncQuery: true,
    });

    return PendingTaskSchema.parse(response);
  };

  return {
    queryHistoricalAssetPrices,
    queryLatestAssetValueDistribution,
    queryLatestLocationValueDistribution,
    queryNetValueData,
    queryStatisticsRenderer,
    queryTimedBalancesData,
    queryTimedHistoricalBalancesData,
  };
}
