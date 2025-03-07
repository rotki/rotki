import type { AllBalancePayload } from '@/types/blockchain/accounts';
import type { PendingTask } from '@/types/task';
import type { ActionResult } from '@rotki/common';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus } from '@/services/utils';

interface UseBalancesApiReturn { queryBalancesAsync: (payload: Partial<AllBalancePayload>) => Promise<PendingTask> }

export function useBalancesApi(): UseBalancesApiReturn {
  const queryBalancesAsync = async (payload: Partial<AllBalancePayload>): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>('/balances', {
      params: snakeCaseTransformer({
        asyncQuery: true,
        ...payload,
      }),
      validateStatus: validStatus,
    });
    return handleResponse(response);
  };

  return {
    queryBalancesAsync,
  };
}
