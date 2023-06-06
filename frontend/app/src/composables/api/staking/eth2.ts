import { type ActionResult } from '@rotki/common/lib/data';
import {
  Eth2DailyStats,
  type Eth2DailyStatsPayload,
  Eth2StakingRewards,
  type EthStakingPayload
} from '@rotki/common/lib/staking/eth2';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validWithSessionAndExternalService
} from '@/services/utils';
import { transformCase } from '@/utils/text';
import { type PendingTask } from '@/types/task';

export const useEth2Api = () => {
  const fetchStakingDetails = async (
    payload: EthStakingPayload
  ): Promise<PendingTask> => {
    const response = await api.instance.put<ActionResult<PendingTask>>(
      '/blockchains/eth2/stake/details',
      snakeCaseTransformer({
        asyncQuery: true,
        ...nonEmptyProperties(payload)
      }),
      {
        validateStatus: validWithSessionAndExternalService
      }
    );
    return handleResponse(response);
  };

  const fetchStakingDetailRewards = async (
    payload: EthStakingPayload
  ): Promise<Eth2StakingRewards> => {
    const response = await api.instance.post<ActionResult<Eth2StakingRewards>>(
      '/blockchains/eth2/stake/details',
      snakeCaseTransformer(nonEmptyProperties(payload)),
      {
        validateStatus: validWithSessionAndExternalService
      }
    );
    return Eth2StakingRewards.parse(handleResponse(response));
  };

  const stakingStatsQuery = async <T>(
    payload: any,
    asyncQuery: boolean
  ): Promise<T> => {
    const response = await api.instance.post<ActionResult<T>>(
      '/blockchains/eth2/stake/dailystats',
      snakeCaseTransformer({
        asyncQuery,
        ...payload,
        orderByAttributes:
          payload.orderByAttributes?.map((item: string) =>
            transformCase(item)
          ) ?? []
      }),
      {
        validateStatus: validWithSessionAndExternalService
      }
    );
    return handleResponse(response);
  };

  const refreshStakingStats = async (
    payload: Eth2DailyStatsPayload
  ): Promise<PendingTask> => stakingStatsQuery(payload, true);

  const fetchStakingStats = async (
    payload: Eth2DailyStatsPayload
  ): Promise<Eth2DailyStats> => {
    const stats = await stakingStatsQuery<Eth2DailyStats>(payload, false);
    return Eth2DailyStats.parse(stats);
  };

  return {
    fetchStakingDetailRewards,
    fetchStakingDetails,
    refreshStakingStats,
    fetchStakingStats
  };
};
