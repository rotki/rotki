import type { PendingTask } from '@/types/task';
import { type ActionResult, type EthStakingPayload, EthStakingPerformanceResponse } from '@rotki/common';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validWithSessionAndExternalService } from '@/services/utils';
import { nonEmptyProperties } from '@/utils/data';

interface UseEth2ApiReturn {
  fetchStakingPerformance: (payload: EthStakingPayload) => Promise<EthStakingPerformanceResponse>;
  refreshStakingPerformance: (payload: EthStakingPayload) => Promise<PendingTask>;
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

  return {
    fetchStakingPerformance,
    refreshStakingPerformance,
  };
}
