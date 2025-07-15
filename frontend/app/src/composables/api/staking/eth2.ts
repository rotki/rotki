import type { PendingTask } from '@/types/task';
import { type ActionResult, Eth2DailyStats, type Eth2DailyStatsPayload, type EthStakingPayload, EthStakingPerformanceResponse, transformCase } from '@rotki/common';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validWithSessionAndExternalService } from '@/services/utils';
import { nonEmptyProperties } from '@/utils/data';

interface UseEth2ApiReturn {
  fetchStakingPerformance: (payload: EthStakingPayload) => Promise<EthStakingPerformanceResponse>;
  refreshStakingPerformance: (payload: EthStakingPayload) => Promise<PendingTask>;
  refreshStakingStats: (payload: Eth2DailyStatsPayload) => Promise<PendingTask>;
  fetchStakingStats: (payload: Eth2DailyStatsPayload) => Promise<Eth2DailyStats>;
}

export function useEth2Api(): UseEth2ApiReturn {
  const stakingPerformanceQuery = async <T extends EthStakingPerformanceResponse | PendingTask>(
    payload: EthStakingPayload & { ignoreCache: boolean },
    asyncQuery: boolean = false,
  ): Promise<T> => {
    const response = await api.instance.put<ActionResult<T>>(
      '/blockchains/eth2/stake/performance',
      snakeCaseTransformer({
        asyncQuery,
        ...nonEmptyProperties(payload),
      }),
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );
    return handleResponse(response);
  };

  const fetchStakingPerformance = async (payload: EthStakingPayload): Promise<EthStakingPerformanceResponse> => {
    const data = await stakingPerformanceQuery({ ...payload, ignoreCache: false });
    return EthStakingPerformanceResponse.parse(data);
  };

  const refreshStakingPerformance = async (payload: EthStakingPayload): Promise<PendingTask> =>
    stakingPerformanceQuery({ ...payload, ignoreCache: true }, true);

  const stakingStatsQuery = async <T>(payload: Eth2DailyStatsPayload, asyncQuery: boolean): Promise<T> => {
    const response = await api.instance.post<ActionResult<T>>(
      '/blockchains/eth2/stake/dailystats',
      snakeCaseTransformer({
        asyncQuery,
        ...payload,
        orderByAttributes: payload.orderByAttributes?.map((item: string) => transformCase(item)) ?? [],
      }),
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );
    return handleResponse(response);
  };

  const refreshStakingStats = async (payload: Eth2DailyStatsPayload): Promise<PendingTask> =>
    stakingStatsQuery(payload, true);

  const fetchStakingStats = async (payload: Eth2DailyStatsPayload): Promise<Eth2DailyStats> => {
    const stats = await stakingStatsQuery<Eth2DailyStats>(payload, false);
    return Eth2DailyStats.parse(stats);
  };

  return {
    fetchStakingPerformance,
    fetchStakingStats,
    refreshStakingPerformance,
    refreshStakingStats,
  };
}
