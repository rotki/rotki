import { type ActionResult } from '@rotki/common/lib/data';
import {
  Eth2DailyStats,
  type Eth2DailyStatsPayload
} from '@rotki/common/lib/staking/eth2';
import {
  snakeCaseTransformer,
  getUpdatedKey
} from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validWithSessionAndExternalService
} from '@/services/utils';
import { type PendingTask } from '@/types/task';

export const useEth2Api = () => {
  const eth2StakingDetails = async (): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>(
      '/blockchains/ETH2/stake/details',
      {
        params: snakeCaseTransformer({
          asyncQuery: true
        }),
        validateStatus: validWithSessionAndExternalService
      }
    );
    return handleResponse(response);
  };

  const eth2StakingDeposits = async (): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>(
      '/blockchains/ETH2/stake/deposits',
      {
        params: snakeCaseTransformer({
          asyncQuery: true
        }),
        validateStatus: validWithSessionAndExternalService
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
      snakeCaseTransformer({
        asyncQuery,
        ...payload,
        orderByAttributes:
          payload.orderByAttributes?.map((item: string) =>
            getUpdatedKey(item, false)
          ) ?? []
      }),
      {
        validateStatus: validWithSessionAndExternalService
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
