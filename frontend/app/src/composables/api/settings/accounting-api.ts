import { omit } from 'es-toolkit';
import {
  type AccountingRule,
  type AccountingRuleConflict,
  AccountingRuleConflictCollectionResponse,
  type AccountingRuleConflictRequestPayload,
  type AccountingRuleConflictResolution,
  type AccountingRuleEntry,
  AccountingRuleEntryCollectionResponse,
  type AccountingRuleRequestPayload,
} from '@/types/settings/accounting';
import { handleResponse, validStatus } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import type { PendingTask } from '@/types/task';
import type { CollectionResponse } from '@/types/collection';
import type { ActionResult } from '@rotki/common';

interface UseAccountingApiReturn {
  fetchAccountingRule: (payload: AccountingRuleRequestPayload, counterparty: string | null) => Promise<AccountingRuleEntry | null>;
  fetchAccountingRules: (payload: AccountingRuleRequestPayload) => Promise<CollectionResponse<AccountingRuleEntry>>;
  addAccountingRule: (payload: AccountingRule) => Promise<boolean>;
  editAccountingRule: (payload: AccountingRuleEntry) => Promise<boolean>;
  deleteAccountingRule: (identifier: number) => Promise<boolean>;
  getAccountingRuleLinkedMapping: () => Promise<Record<string, string[]>>;
  fetchAccountingRuleConflicts: (payload: AccountingRuleConflictRequestPayload) => Promise<CollectionResponse<AccountingRuleConflict>>;
  resolveAccountingRuleConflicts: (payload: AccountingRuleConflictResolution) => Promise<boolean>;
  exportAccountingRules: (directoryPath?: string) => Promise<PendingTask>;
  importAccountingRulesData: (filepath: string) => Promise<PendingTask>;
  uploadAccountingRulesData: (filepath: File) => Promise<PendingTask>;
}

export function useAccountingApi(): UseAccountingApiReturn {
  const fetchAccountingRule = async (
    payload: AccountingRuleRequestPayload,
    counterparty: string | null,
  ): Promise<AccountingRuleEntry | null> => {
    const newPayload = {
      ...omit(payload, ['orderByAttributes', 'ascending']),
      counterparties: counterparty ? [counterparty, null] : [null],
    };
    const response = await api.instance.post<ActionResult<CollectionResponse<AccountingRuleEntry>>>(
      '/accounting/rules',
      snakeCaseTransformer(newPayload),
      {
        validateStatus: validStatus,
      },
    );

    const data = AccountingRuleEntryCollectionResponse.parse(handleResponse(response));

    if (data.entries.length === 0)
      return null;

    if (data.entries.length === 1)
      return data.entries[0];

    if (data.entries.length > 1)
      return data.entries.find(item => item.counterparty === counterparty) || null;

    return null;
  };
  const fetchAccountingRules = async (
    payload: AccountingRuleRequestPayload,
  ): Promise<CollectionResponse<AccountingRuleEntry>> => {
    const response = await api.instance.post<ActionResult<CollectionResponse<AccountingRuleEntry>>>(
      '/accounting/rules',
      snakeCaseTransformer(omit(payload, ['orderByAttributes', 'ascending'])),
      {
        validateStatus: validStatus,
      },
    );

    return AccountingRuleEntryCollectionResponse.parse(handleResponse(response));
  };

  const addAccountingRule = async (payload: AccountingRule): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>('/accounting/rules', snakeCaseTransformer(payload), {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const editAccountingRule = async (payload: AccountingRuleEntry): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      '/accounting/rules',
      snakeCaseTransformer(payload),
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  const deleteAccountingRule = async (identifier: number): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/accounting/rules', {
      data: snakeCaseTransformer({ identifier }),
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const getAccountingRuleLinkedMapping = async (): Promise<Record<string, string[]>> => {
    const response = await api.instance.get<ActionResult<Record<string, string[]>>>('/accounting/rules/info', {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const fetchAccountingRuleConflicts = async (
    payload: AccountingRuleConflictRequestPayload,
  ): Promise<CollectionResponse<AccountingRuleConflict>> => {
    const response = await api.instance.post<ActionResult<any>>(
      '/accounting/rules/conflicts',
      snakeCaseTransformer(omit(payload, ['orderByAttributes', 'ascending'])),
      {
        validateStatus: validStatus,
      },
    );

    return AccountingRuleConflictCollectionResponse.parse(handleResponse(response));
  };

  const resolveAccountingRuleConflicts = async (payload: AccountingRuleConflictResolution): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<any>>(
      '/accounting/rules/conflicts',
      snakeCaseTransformer(payload),
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  const exportAccountingRules = async (directoryPath?: string): Promise<PendingTask> => {
    const response = await api.instance.post<ActionResult<PendingTask>>(
      '/accounting/rules/export',
      snakeCaseTransformer({
        asyncQuery: true,
        directoryPath,
      }),
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  const importAccountingRulesData = async (filepath: string): Promise<PendingTask> => {
    const response = await api.instance.put<ActionResult<PendingTask>>(
      '/accounting/rules/import',
      snakeCaseTransformer({
        asyncQuery: true,
        filepath,
      }),
      {
        validateStatus: validStatus,
      },
    );
    return handleResponse(response);
  };

  const uploadAccountingRulesData = async (filepath: File): Promise<PendingTask> => {
    const data = new FormData();
    data.append('filepath', filepath);
    data.append('async_query', 'true');
    const response = await api.instance.patch<ActionResult<PendingTask>>('/accounting/rules/import', data, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return handleResponse(response);
  };

  return {
    addAccountingRule,
    deleteAccountingRule,
    editAccountingRule,
    exportAccountingRules,
    fetchAccountingRule,
    fetchAccountingRuleConflicts,
    fetchAccountingRules,
    getAccountingRuleLinkedMapping,
    importAccountingRulesData,
    resolveAccountingRuleConflicts,
    uploadAccountingRulesData,
  };
}
