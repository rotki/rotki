import { ActionResult } from '@rotki/common/lib/data';
import {
  LocationData,
  NetValue,
  TimedAssetBalances,
  TimedBalances
} from '@rotki/common/lib/statistics';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { basicAxiosTransformer } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus } from '@/services/utils';

export const useStatisticsApi = () => {
  const queryNetValueData = async (includeNfts: boolean): Promise<NetValue> => {
    const response = await api.instance.get<ActionResult<NetValue>>(
      '/statistics/netvalue',
      {
        params: axiosSnakeCaseTransformer({
          includeNfts
        }),
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const queryTimedBalancesData = async (
    asset: string,
    fromTimestamp: number,
    toTimestamp: number
  ): Promise<TimedBalances> => {
    const balances = await api.instance.post<ActionResult<TimedBalances>>(
      `/statistics/balance`,
      axiosSnakeCaseTransformer({
        fromTimestamp,
        toTimestamp,
        asset
      }),
      {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return TimedBalances.parse(handleResponse(balances));
  };

  const queryLatestLocationValueDistribution =
    async (): Promise<LocationData> => {
      const statistics = await api.instance.get<ActionResult<LocationData>>(
        '/statistics/value_distribution',
        {
          params: axiosSnakeCaseTransformer({ distributionBy: 'location' }),
          validateStatus: validStatus,
          transformResponse: basicAxiosTransformer
        }
      );
      return LocationData.parse(handleResponse(statistics));
    };

  const queryLatestAssetValueDistribution =
    async (): Promise<TimedAssetBalances> => {
      const statistics = await api.instance.get<
        ActionResult<TimedAssetBalances>
      >('/statistics/value_distribution', {
        params: axiosSnakeCaseTransformer({ distributionBy: 'asset' }),
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      });
      return TimedAssetBalances.parse(handleResponse(statistics));
    };

  const queryStatisticsRenderer = async (): Promise<string> => {
    const response = await api.instance.get<ActionResult<string>>(
      '/statistics/renderer',
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  return {
    queryNetValueData,
    queryTimedBalancesData,
    queryLatestLocationValueDistribution,
    queryLatestAssetValueDistribution,
    queryStatisticsRenderer
  };
};
