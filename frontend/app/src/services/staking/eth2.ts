import { ActionResult } from '@rotki/common/lib/data';
import {
  Eth2DailyStats,
  Eth2DailyStatsPayload
} from '@rotki/common/lib/staking/eth2';
import {
  axiosSnakeCaseTransformer,
  getUpdatedKey
} from '@/services/axios-tranformers';
import { basicAxiosTransformer } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { PendingTask } from '@/services/types-api';
import {
  handleResponse,
  validWithSessionAndExternalService
} from '@/services/utils';

export const useEth2Api = () => {
  const eth2StakingDetails = async (): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>(
      '/blockchains/ETH2/stake/details',
      {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true
        }),
        validateStatus: validWithSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );
    return handleResponse(response);
  };

  const eth2StakingDeposits = async (): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>(
      '/blockchains/ETH2/stake/deposits',
      {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true
        }),
        validateStatus: validWithSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );
    return handleResponse(response);
  };

  const internalEth2Stats = async <T>(
    payload: any,
    asyncQuery: boolean
  ): Promise<T> => {
    const response = await api.instance.post<ActionResult<T>>(
      '/blockchains/ETH2/stake/dailystats',
      axiosSnakeCaseTransformer({
        asyncQuery,
        ...payload,
        orderByAttributes:
          payload.orderByAttributes?.map((item: string) =>
            getUpdatedKey(item, false)
          ) ?? []
      }),
      {
        validateStatus: validWithSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );
    return handleResponse(response);
  };

  const eth2StatsTask = async (
    payload: Eth2DailyStatsPayload
  ): Promise<PendingTask> => {
    return internalEth2Stats(payload, true);
  };

  const eth2Stats = async (
    payload: Eth2DailyStatsPayload
  ): Promise<Eth2DailyStats> => {
    const stats = await internalEth2Stats<Eth2DailyStats>(payload, false);
    return Eth2DailyStats.parse(stats);
  };

  return {
    eth2StakingDetails,
    eth2StakingDeposits,
    eth2StatsTask,
    eth2Stats
  };
};
