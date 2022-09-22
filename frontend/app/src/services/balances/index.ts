import { ActionResult } from '@rotki/common/lib/data';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { basicAxiosTransformer } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { PendingTask } from '@/services/types-api';
import { handleResponse, validStatus } from '@/services/utils';
import { AllBalancePayload } from '@/store/balances/types';

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
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );
    return handleResponse(response);
  };

  return {
    queryBalancesAsync
  };
};
