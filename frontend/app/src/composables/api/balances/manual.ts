import { type ActionResult } from '@rotki/common/lib/data';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validWithParamsSessionAndExternalService,
  validWithSessionAndExternalService
} from '@/services/utils';
import { type ManualBalance, ManualBalances } from '@/types/manual-balances';
import { type PendingTask } from '@/types/task';

export const useManualBalancesApi = () => {
  const queryManualBalances = async (): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>(
      'balances/manual',
      {
        params: snakeCaseTransformer({ asyncQuery: true }),
        validateStatus: validWithSessionAndExternalService
      }
    );
    return handleResponse(response);
  };

  const addManualBalances = async (
    balances: Omit<ManualBalance, 'id'>[]
  ): Promise<PendingTask> => {
    const response = await api.instance.put<ActionResult<PendingTask>>(
      'balances/manual',
      snakeCaseTransformer(nonEmptyProperties({ balances, asyncQuery: true })),
      {
        validateStatus: validWithParamsSessionAndExternalService
      }
    );
    return handleResponse(response);
  };

  const editManualBalances = async (
    balances: ManualBalance[]
  ): Promise<PendingTask> => {
    const response = await api.instance.patch<ActionResult<PendingTask>>(
      'balances/manual',
      snakeCaseTransformer(nonEmptyProperties({ balances, asyncQuery: true })),
      {
        validateStatus: validWithParamsSessionAndExternalService
      }
    );
    return handleResponse(response);
  };

  const deleteManualBalances = async (
    ids: number[]
  ): Promise<ManualBalances> => {
    const response = await api.instance.delete<ActionResult<ManualBalances>>(
      'balances/manual',
      {
        data: { ids },
        validateStatus: validWithParamsSessionAndExternalService
      }
    );
    return ManualBalances.parse(handleResponse(response));
  };

  return {
    addManualBalances,
    editManualBalances,
    deleteManualBalances,
    queryManualBalances
  };
};
