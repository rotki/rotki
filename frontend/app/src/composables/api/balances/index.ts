import type { AllBalancePayload } from '@/types/blockchain/accounts';
import { api } from '@/modules/api/rotki-api';
import { type PendingTask, PendingTaskSchema } from '@/types/task';

interface UseBalancesApiReturn { queryBalancesAsync: (payload: Partial<AllBalancePayload>) => Promise<PendingTask> }

export function useBalancesApi(): UseBalancesApiReturn {
  const queryBalancesAsync = async (payload: Partial<AllBalancePayload>): Promise<PendingTask> => {
    const response = await api.get<PendingTask>('/balances', {
      query: {
        asyncQuery: true,
        ...payload,
      },
    });
    return PendingTaskSchema.parse(response);
  };

  return {
    queryBalancesAsync,
  };
}
