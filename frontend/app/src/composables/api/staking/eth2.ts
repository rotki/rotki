import { type EthStakingPayload, EthStakingPerformanceResponse } from '@rotki/common';
import { api } from '@/modules/api/rotki-api';
import { VALID_WITH_SESSION_AND_EXTERNAL_SERVICE } from '@/modules/api/utils';
import { type PendingTask, PendingTaskSchema } from '@/types/task';

interface UseEth2ApiReturn {
  fetchStakingPerformance: (payload: EthStakingPayload) => Promise<EthStakingPerformanceResponse>;
  refreshStakingPerformance: (payload: EthStakingPayload) => Promise<PendingTask>;
}

export function useEth2Api(): UseEth2ApiReturn {
  const fetchStakingPerformance = async (payload: EthStakingPayload): Promise<EthStakingPerformanceResponse> => {
    const response = await api.put<EthStakingPerformanceResponse>(
      '/blockchains/eth2/stake/performance',
      payload,
      {
        validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
        filterEmptyProperties: true,
      },
    );
    return EthStakingPerformanceResponse.parse(response);
  };

  const refreshStakingPerformance = async (payload: EthStakingPayload): Promise<PendingTask> => {
    const response = await api.put<PendingTask>(
      '/blockchains/eth2/stake/performance',
      {
        ...payload,
        asyncQuery: true,
        ignoreCache: true,
      },
      {
        validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
        filterEmptyProperties: true,
      },
    );
    return PendingTaskSchema.parse(response);
  };

  return {
    fetchStakingPerformance,
    refreshStakingPerformance,
  };
}
