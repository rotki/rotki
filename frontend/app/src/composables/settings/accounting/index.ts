import { TaskType } from '@/types/task-type';
import { jsonTransformer } from '@/services/axios-tranformers';
import type { MaybeRef } from '@vueuse/core';
import type {
  AccountingRuleConflict,
  AccountingRuleConflictRequestPayload,
  AccountingRuleConflictResolution,
  AccountingRuleEntry,
  AccountingRuleRequestPayload,
} from '@/types/settings/accounting';
import type { Collection } from '@/types/collection';
import type { ActionStatus } from '@/types/action';
import type { TaskMeta } from '@/types/task';
import type { Message } from '@rotki/common';

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
    fetchAccountingRule,
    fetchAccountingRules,
    fetchAccountingRuleConflicts,
    resolveAccountingRuleConflicts: resolveAccountingRuleConflictsCaller,
    exportAccountingRules,
    importAccountingRulesData,
    uploadAccountingRulesData,
  } = useAccountingApi();

  const { t } = useI18n();

  const { notify } = useNotificationsStore();

  const getAccountingRule = async (
    payload: MaybeRef<AccountingRuleRequestPayload>,
    counterparty: string | null,
  ): Promise<AccountingRuleEntry | undefined> => {
    try {
      return await fetchAccountingRule(get(payload), counterparty) ?? undefined;
    }
    catch (error: any) {
      logger.error(error);
      const message = error?.message ?? error ?? '';

      notify({
        title: t('accounting_settings.rule.fetch_error.title'),
        message: t('accounting_settings.rule.fetch_error.message', {
          message,
        }),
        display: true,
      });

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
    catch (error: any) {
      logger.error(error);
      const message = error?.message ?? error ?? '';

      notify({
        title: t('accounting_settings.rule.fetch_error.title'),
        message: t('accounting_settings.rule.fetch_error.message', {
          message,
        }),
        display: true,
      });

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
    catch (error: any) {
      logger.error(error);
      const message = error?.message ?? error ?? '';

      notify({
        title: t('accounting_settings.rule.conflicts.fetch_error.title'),
        message: t('accounting_settings.rule.conflicts.fetch_error.message', {
          message,
        }),
        display: true,
      });

      return defaultCollectionState();
    }
  };

  const resolveAccountingRuleConflicts = async (payload: AccountingRuleConflictResolution): Promise<ActionStatus> => {
    try {
      await resolveAccountingRuleConflictsCaller(payload);

      return { success: true };
    }
    catch (error: any) {
      logger.error(error);
      return { success: false, message: error.message };
    }
  };

  const { setMessage } = useMessageStore();
  const { awaitTask } = useTaskStore();

  const exportAccountingRulesData = async (
    directoryPath?: string,
  ): Promise<{ result: boolean | object; message?: string } | null> => {
    try {
      const { taskId } = await exportAccountingRules(directoryPath);
      const { result } = await awaitTask<boolean | object, TaskMeta>(taskId, TaskType.EXPORT_ACCOUNTING_RULES, {
        title: t('actions.accounting_rules.export.title'),
        transformer: [jsonTransformer],
      });

      return {
        result,
      };
    }
    catch (error: any) {
      if (!isTaskCancelled(error))
        return null;

      return {
        result: false,
        message: error.message,
      };
    }
  };

  const { appSession, getPath, openDirectory } = useInterop();

  async function exportJSON(): Promise<void> {
    let message: Message | null = null;

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

      const { result, message: taskMessage } = response;

      if (appSession) {
        message = {
          title: t('actions.accounting_rules.export.title'),
          description: result
            ? t('actions.accounting_rules.export.message.success')
            : t('actions.accounting_rules.export.message.failure', {
              description: taskMessage,
            }),
          success: !!result,
        };
      }
      else {
        downloadFileByTextContent(JSON.stringify(result, null, 2), 'accounting_rules.json', 'application/json');
      }
    }
    catch (error: any) {
      message = {
        title: t('actions.accounting_rules.export.title'),
        description: t('actions.accounting_rules.export.message.failure', {
          description: error.message,
        }),
        success: false,
      };
    }

    if (message)
      setMessage(message);
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
    catch (error: any) {
      if (isTaskCancelled(error))
        return null;

      message = error.message;
      success = false;
    }

    return { success, message };
  }

  return {
    getAccountingRule,
    getAccountingRules,
    getAccountingRulesConflicts,
    resolveAccountingRuleConflicts,
    exportJSON,
    importJSON,
  };
}
