import { api } from '@/modules/api/rotki-api';
import { VALID_WITH_SESSION_AND_EXTERNAL_SERVICE } from '@/modules/api/utils';
import { type PendingTask, PendingTaskSchema } from '@/types/task';

interface UseLiquityApiReturn {
  fetchLiquityBalances: () => Promise<PendingTask>;
  fetchLiquityStaking: () => Promise<PendingTask>;
  fetchLiquityStakingPools: () => Promise<PendingTask>;
  fetchLiquityStatistics: () => Promise<PendingTask>;
}

export function useLiquityApi(): UseLiquityApiReturn {
  const fetchLiquityBalances = async (): Promise<PendingTask> => {
    const response = await api.get<PendingTask>('blockchains/eth/modules/liquity/balances', {
      query: { asyncQuery: true },
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    });
    return PendingTaskSchema.parse(response);
  };

  const fetchLiquityStaking = async (): Promise<PendingTask> => {
    const response = await api.get<PendingTask>('blockchains/eth/modules/liquity/staking', {
      query: { asyncQuery: true },
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    });
    return PendingTaskSchema.parse(response);
  };

  const fetchLiquityStakingPools = async (): Promise<PendingTask> => {
    const response = await api.get<PendingTask>('blockchains/eth/modules/liquity/pool', {
      query: { asyncQuery: true },
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    });
    return PendingTaskSchema.parse(response);
  };

  const fetchLiquityStatistics = async (): Promise<PendingTask> => {
    const response = await api.get<PendingTask>('blockchains/eth/modules/liquity/stats', {
      query: { asyncQuery: true },
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    });
    return PendingTaskSchema.parse(response);
  };

  return {
    fetchLiquityBalances,
    fetchLiquityStaking,
    fetchLiquityStakingPools,
    fetchLiquityStatistics,
  };
}
