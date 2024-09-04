import { type ActionResult, LocationData, NetValue, TimedAssetBalances, TimedBalances } from '@rotki/common';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus } from '@/services/utils';

interface UseStatisticsApiReturn {
  queryNetValueData: (includeNfts: boolean) => Promise<NetValue>;
  queryTimedBalancesData: (asset: string, fromTimestamp: number, toTimestamp: number, collectionId?: number) => Promise<TimedBalances>;
  queryLatestLocationValueDistribution: () => Promise<LocationData>;
  queryLatestAssetValueDistribution: () => Promise<TimedAssetBalances>;
  queryStatisticsRenderer: () => Promise<string>;
}

export function useStatisticsApi(): UseStatisticsApiReturn {
  const queryNetValueData = async (includeNfts: boolean): Promise<NetValue> => {
    const response = await api.instance.get<ActionResult<NetValue>>('/statistics/netvalue', {
      params: snakeCaseTransformer({
        includeNfts,
      }),
      validateStatus: validStatus,
    });

    return NetValue.parse(handleResponse(response));
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
    const balances = await api.instance.post<ActionResult<TimedBalances>>(
      `/statistics/balance`,
      snakeCaseTransformer(payload),
      {
        validateStatus: validStatus,
      },
    );

    return TimedBalances.parse(handleResponse(balances));
  };

  const queryLatestLocationValueDistribution = async (): Promise<LocationData> => {
    const statistics = await api.instance.get<ActionResult<LocationData>>('/statistics/value_distribution', {
      params: snakeCaseTransformer({ distributionBy: 'location' }),
      validateStatus: validStatus,
    });
    return LocationData.parse(handleResponse(statistics));
  };

  const queryLatestAssetValueDistribution = async (): Promise<TimedAssetBalances> => {
    const statistics = await api.instance.get<ActionResult<TimedAssetBalances>>('/statistics/value_distribution', {
      params: snakeCaseTransformer({ distributionBy: 'asset' }),
      validateStatus: validStatus,
    });
    return TimedAssetBalances.parse(handleResponse(statistics));
  };

  const queryStatisticsRenderer = async (): Promise<string> => {
    const response = await api.instance.get<ActionResult<string>>('/statistics/renderer', {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  return {
    queryNetValueData,
    queryTimedBalancesData,
    queryLatestLocationValueDistribution,
    queryLatestAssetValueDistribution,
    queryStatisticsRenderer,
  };
}
