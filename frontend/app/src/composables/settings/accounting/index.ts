import type { MaybeRef } from 'vue';
import type { ActionStatus } from '@/types/action';
import type { Collection } from '@/types/collection';
import type {
  AccountingRuleConflict,
  AccountingRuleConflictRequestPayload,
  AccountingRuleConflictResolution,
  AccountingRuleEntry,
  AccountingRuleRequestPayload,
} from '@/types/settings/accounting';
import type { TaskMeta } from '@/types/task';
import { useAccountingApi } from '@/composables/api/settings/accounting-api';
import { useInterop } from '@/composables/electron-interop';
import { getErrorMessage, useNotifications } from '@/modules/notifications/use-notifications';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { defaultCollectionState, mapCollectionResponse } from '@/utils/collection';
import { downloadFileByTextContent } from '@/utils/download';
import { logger } from '@/utils/logging';

interface UseAccountingSettingReturn {
  getAccountingRule: (payload: MaybeRef<AccountingRuleRequestPayload>, counterparty: string | null) => Promise<AccountingRuleEntry | undefined>;
  getAccountingRules: (payload: MaybeRef<AccountingRuleRequestPayload>) => Promise<Collection<AccountingRuleEntry>>;
  getAccountingRulesConflicts: (payload: MaybeRef<AccountingRuleConflictRequestPayload>) => Promise<Collection<AccountingRuleConflict>>;
  resolveAccountingRuleConflicts: (payload: AccountingRuleConflictResolution) => Promise<ActionStatus>;
  exportJSON: () => Promise<void>;
  importJSON: (file: File) => Promise<ActionStatus | null>;
}

export function useAccountingSettings(): UseAccountingSettingReturn {
  const {
    exportAccountingRules,
    fetchAccountingRule,
    fetchAccountingRuleConflicts,
    fetchAccountingRules,
    importAccountingRulesData,
    resolveAccountingRuleConflicts: resolveAccountingRuleConflictsCaller,
    uploadAccountingRulesData,
  } = useAccountingApi();

  const { t } = useI18n({ useScope: 'global' });

  const { notifyError, showErrorMessage, showSuccessMessage } = useNotifications();

  const getAccountingRule = async (
    payload: MaybeRef<AccountingRuleRequestPayload>,
    counterparty: string | null,
  ): Promise<AccountingRuleEntry | undefined> => {
    try {
      return await fetchAccountingRule(get(payload), counterparty) ?? undefined;
    }
    catch (error: unknown) {
      logger.error(error);
      const message = getErrorMessage(error);

      notifyError(
        t('accounting_settings.rule.fetch_error.title'),
        t('accounting_settings.rule.fetch_error.message', {
          message,
        }),
      );

      return undefined;
    }
  };

  const getAccountingRules = async (
    payload: MaybeRef<AccountingRuleRequestPayload>,
  ): Promise<Collection<AccountingRuleEntry>> => {
    try {
      const response = await fetchAccountingRules(get(payload));

      return mapCollectionResponse(response);
    }
    catch (error: unknown) {
      logger.error(error);
      const message = getErrorMessage(error);

      notifyError(
        t('accounting_settings.rule.fetch_error.title'),
        t('accounting_settings.rule.fetch_error.message', {
          message,
        }),
      );

      return defaultCollectionState();
    }
  };

  const getAccountingRulesConflicts = async (
    payload: MaybeRef<AccountingRuleConflictRequestPayload>,
  ): Promise<Collection<AccountingRuleConflict>> => {
    try {
      const response = await fetchAccountingRuleConflicts(get(payload));

      return mapCollectionResponse(response);
    }
    catch (error: unknown) {
      logger.error(error);
      const message = getErrorMessage(error);

      notifyError(
        t('accounting_settings.rule.conflicts.fetch_error.title'),
        t('accounting_settings.rule.conflicts.fetch_error.message', {
          message,
        }),
      );

      return defaultCollectionState();
    }
  };

  const resolveAccountingRuleConflicts = async (payload: AccountingRuleConflictResolution): Promise<ActionStatus> => {
    try {
      await resolveAccountingRuleConflictsCaller(payload);

      return { success: true };
    }
    catch (error: unknown) {
      logger.error(error);
      return { message: getErrorMessage(error), success: false };
    }
  };

  const { awaitTask } = useTaskStore();

  const exportAccountingRulesData = async (
    directoryPath?: string,
  ): Promise<{ result: boolean | object; message?: string } | null> => {
    try {
      const { taskId } = await exportAccountingRules(directoryPath);
      const { result } = await awaitTask<boolean | object, TaskMeta>(taskId, TaskType.EXPORT_ACCOUNTING_RULES, {
        title: t('actions.accounting_rules.export.title'),
      });

      return {
        result,
      };
    }
    catch (error: unknown) {
      if (!isTaskCancelled(error))
        return null;

      return {
        message: getErrorMessage(error),
        result: false,
      };
    }
  };

  const { appSession, getPath, openDirectory } = useInterop();

  async function exportJSON(): Promise<void> {
    const title = t('actions.accounting_rules.export.title');

    try {
      let directoryPath;
      if (appSession) {
        directoryPath = await openDirectory(t('common.select_directory'));
        if (!directoryPath)
          return;
      }

      const response = await exportAccountingRulesData(directoryPath);
      if (response === null)
        return;

      const { message: taskMessage, result } = response;

      if (appSession) {
        if (result) {
          showSuccessMessage(title, t('actions.accounting_rules.export.message.success'));
        }
        else {
          showErrorMessage(title, t('actions.accounting_rules.export.message.failure', {
            description: taskMessage,
          }));
        }
      }
      else {
        downloadFileByTextContent(JSON.stringify(result, null, 2), 'accounting_rules.json', 'application/json');
      }
    }
    catch (error: unknown) {
      showErrorMessage(title, t('actions.accounting_rules.export.message.failure', {
        description: getErrorMessage(error),
      }));
    }
  }

  async function importJSON(file: File): Promise<ActionStatus | null> {
    let success: boolean;
    let message = '';

    const taskType = TaskType.IMPORT_ACCOUNTING_RULES;

    try {
      const path = getPath(file);
      const { taskId } = path
        ? await importAccountingRulesData(path)
        : await uploadAccountingRulesData(file);

      const { result } = await awaitTask<boolean, TaskMeta>(taskId, taskType, {
        title: t('actions.accounting_rules.import.title'),
      });
      success = result;
    }
    catch (error: unknown) {
      if (isTaskCancelled(error))
        return null;

      message = getErrorMessage(error);
      success = false;
    }

    return { message, success };
  }

  return {
    exportJSON,
    getAccountingRule,
    getAccountingRules,
    getAccountingRulesConflicts,
    importJSON,
    resolveAccountingRuleConflicts,
  };
}
