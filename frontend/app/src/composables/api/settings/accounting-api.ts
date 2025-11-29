import type { CollectionResponse } from '@/types/collection';
import { omit } from 'es-toolkit';
import { api } from '@/modules/api/rotki-api';
import {
  type AccountingRule,
  type AccountingRuleConflict,
  AccountingRuleConflictCollectionResponse,
  type AccountingRuleConflictRequestPayload,
  type AccountingRuleConflictResolution,
  type AccountingRuleEntry,
  AccountingRuleEntryCollectionResponse,
  type AccountingRuleLinkedMapping,
  AccountingRuleLinkedMappingSchema,
  type AccountingRuleRequestPayload,
} from '@/types/settings/accounting';
import { type PendingTask, PendingTaskSchema } from '@/types/task';

interface UseAccountingApiReturn {
  fetchAccountingRule: (payload: AccountingRuleRequestPayload, counterparty: string | null) => Promise<AccountingRuleEntry | null>;
  fetchAccountingRules: (payload: AccountingRuleRequestPayload) => Promise<CollectionResponse<AccountingRuleEntry>>;
  addAccountingRule: (payload: AccountingRule) => Promise<boolean>;
  editAccountingRule: (payload: AccountingRuleEntry) => Promise<boolean>;
  deleteAccountingRule: (identifier: number) => Promise<boolean>;
  getAccountingRuleLinkedMapping: () => Promise<AccountingRuleLinkedMapping>;
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
    const response = await api.post<CollectionResponse<AccountingRuleEntry>>(
      '/accounting/rules',
      newPayload,
    );

    const data = AccountingRuleEntryCollectionResponse.parse(response);

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
    const response = await api.post<CollectionResponse<AccountingRuleEntry>>(
      '/accounting/rules',
      omit(payload, ['orderByAttributes', 'ascending']),
    );

    return AccountingRuleEntryCollectionResponse.parse(response);
  };

  const addAccountingRule = async (payload: AccountingRule): Promise<boolean> => api.put<boolean>('/accounting/rules', payload);

  const editAccountingRule = async (payload: AccountingRuleEntry): Promise<boolean> => api.patch<boolean>('/accounting/rules', payload);

  const deleteAccountingRule = async (identifier: number): Promise<boolean> => api.delete<boolean>('/accounting/rules', {
    body: { identifier },
  });

  const getAccountingRuleLinkedMapping = async (): Promise<AccountingRuleLinkedMapping> => {
    const response = await api.get<AccountingRuleLinkedMapping>('/accounting/rules/info');
    return AccountingRuleLinkedMappingSchema.parse(response);
  };

  const fetchAccountingRuleConflicts = async (
    payload: AccountingRuleConflictRequestPayload,
  ): Promise<CollectionResponse<AccountingRuleConflict>> => {
    const response = await api.post<CollectionResponse<AccountingRuleConflict>>(
      '/accounting/rules/conflicts',
      omit(payload, ['orderByAttributes', 'ascending']),
    );

    return AccountingRuleConflictCollectionResponse.parse(response);
  };

  const resolveAccountingRuleConflicts = async (payload: AccountingRuleConflictResolution): Promise<boolean> => api.patch<boolean>('/accounting/rules/conflicts', payload);

  const exportAccountingRules = async (directoryPath?: string): Promise<PendingTask> => {
    const response = await api.post<PendingTask>(
      '/accounting/rules/export',
      {
        asyncQuery: true,
        directoryPath,
      },
    );
    return PendingTaskSchema.parse(response);
  };

  const importAccountingRulesData = async (filepath: string): Promise<PendingTask> => {
    const response = await api.put<PendingTask>(
      '/accounting/rules/import',
      {
        asyncQuery: true,
        filepath,
      },
    );
    return PendingTaskSchema.parse(response);
  };

  const uploadAccountingRulesData = async (filepath: File): Promise<PendingTask> => {
    const data = new FormData();
    data.append('filepath', filepath);
    data.append('async_query', 'true');
    const response = await api.patch<PendingTask>('/accounting/rules/import', data);
    return PendingTaskSchema.parse(response);
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
