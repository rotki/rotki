import { fromAsync, type ResultAsync } from 'plainfp/result-async';
import {
  type BankConnectionEditPayload,
  type BankConnectionIdentity,
  type BankConnectionPayload,
  BankConnections,
  BankManifests,
  type BankSetupError,
  type BankSyncPayload,
} from '@/modules/banks/types';
import { api } from '@/modules/core/api/rotki-api';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { VALID_WITH_SESSION_STATUS } from '@/modules/core/api/utils';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { type PendingTask, PendingTaskSchema } from '@/modules/core/tasks/types';

/** Credential slots are snake_case on the wire; the api error keys arrive camelCased. */
function toCamelCase(slot: string): string {
  return slot.replace(/_([a-z])/g, (_match, letter: string) => letter.toUpperCase());
}

/**
 * Classifies a failed add or edit into a {@link BankSetupError}.
 *
 * @remarks
 * A `400` arrives as an {@link ApiValidationError} with camelCased keys, so a credential error is
 * keyed back to its slot. A validation error naming no field of the payload, and every other
 * failure, is a message for the whole request.
 *
 * @param cause - the value thrown by the failed request
 * @param payload - what was sent, which decides whether an error key names one of its fields
 * @returns the error the dialog branches on
 */
function toBankSetupError(cause: unknown, payload: BankConnectionPayload): BankSetupError {
  if (!(cause instanceof ApiValidationError))
    return { message: getErrorMessage(cause), type: 'rejected' };

  const slotsByKey = new Map<string, string>(Object.keys(payload.credentials).map(slot => [toCamelCase(slot), slot]));
  const errors = cause.getValidationErrors({
    ...payload,
    ...Object.fromEntries(Object.entries(payload.credentials).map(([slot, value]) => [toCamelCase(slot), value])),
  });
  if (typeof errors === 'string')
    return { message: errors, type: 'rejected' };

  return {
    errors: Object.fromEntries(Object.entries(errors).map(([key, value]) => [slotsByKey.get(key) ?? key, value])),
    type: 'fields',
  };
}

interface UseBanksApiReturn {
  getSupportedBanks: () => Promise<BankManifests>;
  getBanks: () => Promise<BankConnections>;
  addBank: (payload: BankConnectionPayload) => ResultAsync<boolean, BankSetupError>;
  editBank: (payload: BankConnectionEditPayload) => ResultAsync<boolean, BankSetupError>;
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

  const addBank = async (payload: BankConnectionPayload): ResultAsync<boolean, BankSetupError> =>
    fromAsync(async () => api.put<boolean>('/banks', payload), cause => toBankSetupError(cause, payload));

  const editBank = async (payload: BankConnectionEditPayload): ResultAsync<boolean, BankSetupError> =>
    fromAsync(
      async () => api.patch<boolean>('/banks', payload, { filterEmptyProperties: { removeEmptyString: true } }),
      cause => toBankSetupError(cause, payload),
    );

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
