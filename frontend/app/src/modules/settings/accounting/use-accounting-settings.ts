import type { MaybeRef } from 'vue';
import type { ActionStatus } from '@/modules/core/common/action';
import type { Collection } from '@/modules/core/common/collection';
import type { TaskMeta } from '@/modules/core/tasks/types';
import type {
  AccountingRuleConflict,
  AccountingRuleConflictRequestPayload,
  AccountingRuleConflictResolution,
  AccountingRuleEntry,
  AccountingRuleRequestPayload,
} from '@/modules/settings/types/accounting';
import { defaultCollectionState, mapCollectionResponse } from '@/modules/core/common/data/collection-utils';
import { downloadFileByTextContent } from '@/modules/core/common/file/download';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { useAccountingApi } from '@/modules/settings/api/use-accounting-api';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

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

  const { runTask } = useTaskHandler();

  const exportAccountingRulesData = async (
    directoryPath?: string,
  ): Promise<{ result: boolean | object; message?: string } | null> => {
    const outcome = await runTask<boolean | object, TaskMeta>(
      async () => exportAccountingRules(directoryPath),
      { type: TaskType.EXPORT_ACCOUNTING_RULES, meta: { title: t('actions.accounting_rules.export.title') } },
    );

    if (outcome.success) {
      return {
        result: outcome.result,
      };
    }

    if (!isActionableFailure(outcome))
      return null;

    return {
      message: outcome.message,
      result: false,
    };
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
    const path = getPath(file);
    const outcome = await runTask<boolean, TaskMeta>(
      async () => path ? importAccountingRulesData(path) : uploadAccountingRulesData(file),
      { type: TaskType.IMPORT_ACCOUNTING_RULES, meta: { title: t('actions.accounting_rules.import.title') } },
    );

    if (outcome.success)
      return { message: '', success: outcome.result };

    if (!isActionableFailure(outcome))
      return null;

    return { message: outcome.message, success: false };
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
