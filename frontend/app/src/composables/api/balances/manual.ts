import { api } from '@/modules/api/rotki-api';
import {
  VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
  VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
} from '@/modules/api/utils';
import { type ManualBalance, ManualBalances, type RawManualBalance } from '@/types/manual-balances';
import { type PendingTask, PendingTaskSchema } from '@/types/task';

interface UseManualBalancesApiReturn {
  addManualBalances: (balances: RawManualBalance[]) => Promise<PendingTask>;
  editManualBalances: (balances: ManualBalance[]) => Promise<PendingTask>;
  deleteManualBalances: (ids: number[]) => Promise<ManualBalances>;
  queryManualBalances: (usdValueThreshold?: string) => Promise<PendingTask>;
}

export function useManualBalancesApi(): UseManualBalancesApiReturn {
  const queryManualBalances = async (usdValueThreshold?: string): Promise<PendingTask> => {
    const response = await api.get<PendingTask>('balances/manual', {
      query: {
        asyncQuery: true,
        usdValueThreshold,
      },
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    });
    return PendingTaskSchema.parse(response);
  };

  const addManualBalances = async (balances: RawManualBalance[]): Promise<PendingTask> => {
    const response = await api.put<PendingTask>(
      'balances/manual',
      { asyncQuery: true, balances },
      {
        filterEmptyProperties: true,
        validStatuses: VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
      },
    );
    return PendingTaskSchema.parse(response);
  };

  const editManualBalances = async (balances: ManualBalance[]): Promise<PendingTask> => {
    const response = await api.patch<PendingTask>(
      'balances/manual',
      { asyncQuery: true, balances },
      {
        filterEmptyProperties: true,
        validStatuses: VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
      },
    );
    return PendingTaskSchema.parse(response);
  };

  const deleteManualBalances = async (ids: number[]): Promise<ManualBalances> => {
    const response = await api.delete<ManualBalances>('balances/manual', {
      body: { ids },
      validStatuses: VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
    });
    return ManualBalances.parse(response);
  };

  return {
    addManualBalances,
    deleteManualBalances,
    editManualBalances,
    queryManualBalances,
  };
}
