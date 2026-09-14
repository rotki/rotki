import {
  type BankConnectionEditPayload,
  type BankConnectionIdentity,
  type BankConnectionPayload,
  BankConnections,
  BankManifests,
  type BankSyncPayload,
} from '@/modules/banks/types';
import { api } from '@/modules/core/api/rotki-api';
import { VALID_WITH_SESSION_STATUS } from '@/modules/core/api/utils';
import { type PendingTask, PendingTaskSchema } from '@/modules/core/tasks/types';

interface UseBanksApiReturn {
  getSupportedBanks: () => Promise<BankManifests>;
  getBanks: () => Promise<BankConnections>;
  addBank: (payload: BankConnectionPayload) => Promise<boolean>;
  editBank: (payload: BankConnectionEditPayload) => Promise<boolean>;
  removeBank: (payload: BankConnectionIdentity) => Promise<boolean>;
  /** Starts a backend task that pulls new transactions; the caller awaits it through the task center. */
  syncBanks: (payload: BankSyncPayload) => Promise<PendingTask>;
  /** Starts a backend task that queries every bank's balances, keyed by location. */
  queryBankBalances: (ignoreCache?: boolean) => Promise<PendingTask>;
}

/**
 * The `/banks` endpoints. A bank connection is set up from its manifest: the credentials are sent
 * keyed by the manifest's secret slots, so this client knows nothing about any particular bank.
 */
export function useBanksApi(): UseBanksApiReturn {
  const getSupportedBanks = async (): Promise<BankManifests> => {
    const data = await api.get<BankManifests>('/banks/supported');
    return BankManifests.parse(data);
  };

  const getBanks = async (): Promise<BankConnections> => {
    const data = await api.get<BankConnections>('/banks', { validStatuses: VALID_WITH_SESSION_STATUS });
    return BankConnections.parse(data);
  };

  const addBank = async (payload: BankConnectionPayload): Promise<boolean> =>
    api.put<boolean>('/banks', payload);

  const editBank = async (payload: BankConnectionEditPayload): Promise<boolean> =>
    api.patch<boolean>('/banks', payload, { filterEmptyProperties: { removeEmptyString: true } });

  const removeBank = async ({ location, name }: BankConnectionIdentity): Promise<boolean> =>
    api.delete<boolean>('/banks', { body: { location, name } });

  const syncBanks = async (payload: BankSyncPayload): Promise<PendingTask> => {
    const response = await api.post<PendingTask>('/banks/sync', { ...payload, asyncQuery: true }, { filterEmptyProperties: true });
    return PendingTaskSchema.parse(response);
  };

  const queryBankBalances = async (ignoreCache = false): Promise<PendingTask> => {
    const response = await api.get<PendingTask>('/banks/balances', {
      query: { asyncQuery: true, ignoreCache: ignoreCache ? true : undefined },
    });
    return PendingTaskSchema.parse(response);
  };

  return {
    addBank,
    editBank,
    getBanks,
    getSupportedBanks,
    queryBankBalances,
    removeBank,
    syncBanks,
  };
}
