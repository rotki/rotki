import { api } from '@/modules/core/api/rotki-api';
import { VALID_WITH_SESSION_AND_EXTERNAL_SERVICE } from '@/modules/core/api/utils';
import { type PendingTask, PendingTaskSchema } from '@/modules/core/tasks/types';

interface UseStakingApiReturn {
  fetchHyperliquidStakingSummaries: () => Promise<PendingTask>;
  fetchSolanaStakeAccounts: () => Promise<PendingTask>;
}

export function useStakingApi(): UseStakingApiReturn {
  const fetchSolanaStakeAccounts = async (): Promise<PendingTask> => {
    const response = await api.get<PendingTask>('/blockchains/solana/stake/accounts', {
      query: { asyncQuery: true },
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    });
    return PendingTaskSchema.parse(response);
  };

  const fetchHyperliquidStakingSummaries = async (): Promise<PendingTask> => {
    const response = await api.get<PendingTask>('/blockchains/hyperliquid/stake/summary', {
      query: { asyncQuery: true },
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    });
    return PendingTaskSchema.parse(response);
  };

  return { fetchHyperliquidStakingSummaries, fetchSolanaStakeAccounts };
}
