import { type ActionResult } from '@rotki/common/lib/data';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus } from '@/services/utils';
import { type PendingTask } from '@/types/task';
import { type AllBalancePayload } from '@/types/blockchain/accounts';

export const useBalancesApi = () => {
  const queryBalancesAsync = async (
    payload: Partial<AllBalancePayload>
  ): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>(
      '/balances',
      {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true,
          ...payload
        }),
        validateStatus: validStatus
      }
    );
    return handleResponse(response);
  };

  return {
    queryBalancesAsync
  };
};
