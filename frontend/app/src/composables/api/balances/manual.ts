import type { PendingTask } from '@/types/task';
import type { ActionResult } from '@rotki/common';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validWithParamsSessionAndExternalService,
  validWithSessionAndExternalService,
} from '@/services/utils';
import { type ManualBalance, ManualBalances, type RawManualBalance } from '@/types/manual-balances';
import { nonEmptyProperties } from '@/utils/data';

interface UseManualBalancesApiReturn {
  addManualBalances: (balances: RawManualBalance[]) => Promise<PendingTask>;
  editManualBalances: (balances: ManualBalance[]) => Promise<PendingTask>;
  deleteManualBalances: (ids: number[]) => Promise<ManualBalances>;
  queryManualBalances: (usdValueThreshold?: string) => Promise<PendingTask>;
}

export function useManualBalancesApi(): UseManualBalancesApiReturn {
  const queryManualBalances = async (usdValueThreshold?: string): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>('balances/manual', {
      params: snakeCaseTransformer({
        asyncQuery: true,
        usdValueThreshold,
      }),
      validateStatus: validWithSessionAndExternalService,
    });
    return handleResponse(response);
  };

  const addManualBalances = async (balances: RawManualBalance[]): Promise<PendingTask> => {
    const response = await api.instance.put<ActionResult<PendingTask>>(
      'balances/manual',
      snakeCaseTransformer(nonEmptyProperties({ asyncQuery: true, balances })),
      {
        validateStatus: validWithParamsSessionAndExternalService,
      },
    );
    return handleResponse(response);
  };

  const editManualBalances = async (balances: ManualBalance[]): Promise<PendingTask> => {
    const response = await api.instance.patch<ActionResult<PendingTask>>(
      'balances/manual',
      snakeCaseTransformer(nonEmptyProperties({ asyncQuery: true, balances })),
      {
        validateStatus: validWithParamsSessionAndExternalService,
      },
    );
    return handleResponse(response);
  };

  const deleteManualBalances = async (ids: number[]): Promise<ManualBalances> => {
    const response = await api.instance.delete<ActionResult<ManualBalances>>('balances/manual', {
      data: { ids },
      validateStatus: validWithParamsSessionAndExternalService,
    });
    return ManualBalances.parse(handleResponse(response));
  };

  return {
    addManualBalances,
    deleteManualBalances,
    editManualBalances,
    queryManualBalances,
  };
}
