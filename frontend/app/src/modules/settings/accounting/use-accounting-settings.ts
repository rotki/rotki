import type { MaybeRef } from 'vue';
import type { ActionStatus } from '@/modules/core/common/action';
import type { Collection } from '@/modules/core/common/collection';
import type {
  AccountingRuleConflict,
  AccountingRuleConflictRequestPayload,
  AccountingRuleConflictResolution,
  AccountingRuleEntry,
  AccountingRuleRequestPayload,
} from '@/modules/settings/types/accounting';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { defaultCollectionState, mapCollectionResponse } from '@/modules/core/common/data/collection-utils';
import { downloadFileByTextContent } from '@/modules/core/common/file/download';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { useAccountingApi } from '@/modules/settings/api/use-accounting-api';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { activityLabel } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseAccountingSettingsReturn {
  getAccountingRule: (payload: MaybeRef<AccountingRuleRequestPayload>, counterparty: string | null) => Promise<AccountingRuleEntry | undefined>;
  getAccountingRules: (payload: MaybeRef<AccountingRuleRequestPayload>) => Promise<Collection<AccountingRuleEntry>>;
  getAccountingRulesConflicts: (payload: MaybeRef<AccountingRuleConflictRequestPayload>) => Promise<Collection<AccountingRuleConflict>>;
  resolveAccountingRuleConflicts: (payload: AccountingRuleConflictResolution) => Promise<ActionStatus>;
  exportJSON: () => Promise<void>;
  importJSON: (file: File) => Promise<ActionStatus | null>;
  resetToDefaults: () => Promise<ActionStatus | null>;
}

export function useAccountingSettings(): UseAccountingSettingsReturn {
  const {
    exportAccountingRules,
    fetchAccountingRule,
    fetchAccountingRuleConflicts,
    fetchAccountingRules,
    importAccountingRulesData,
    resetAccountingRules,
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

  const { submitTask } = useNativeTask();

  const exportAccountingRulesData = async (
    directoryPath?: string,
  ): Promise<{ result: boolean | object; message?: string } | null> => {
    const outcome = await submitTask<boolean | object>({
      id: makeActivityId(ActivityKind.ACCOUNTING_RULES, ActivityPart.EXPORT),
      kind: ActivityKind.ACCOUNTING_RULES,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<boolean | object, TaskError>> => mapResult(
        await runTask<boolean | object>(
          async () => exportAccountingRules(directoryPath),
        ),
        value => value,
      ),
      subtitle: activityLabel(ActivityKind.ACCOUNTING_RULES, ActivityPart.EXPORT),
      title: t('task_center.group.accounting_rules'),
    });

    if (!isErr(outcome)) {
      return {
        result: outcome.value,
      };
    }

    if (!isActionable(outcome.error))
      return null;

    return {
      message: outcome.error.message,
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
    const outcome = await submitTask<boolean>({
      id: makeActivityId(ActivityKind.ACCOUNTING_RULES, ActivityPart.IMPORT),
      kind: ActivityKind.ACCOUNTING_RULES,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<boolean, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => path ? importAccountingRulesData(path) : uploadAccountingRulesData(file),
        ),
        value => value,
      ),
      subtitle: activityLabel(ActivityKind.ACCOUNTING_RULES, ActivityPart.IMPORT, { file: file.name }),
      title: t('task_center.group.accounting_rules'),
    });

    if (!isErr(outcome))
      return { message: '', success: outcome.value };

    if (!isActionable(outcome.error))
      return null;

    return { message: outcome.error.message, success: false };
  }

  async function resetToDefaults(): Promise<ActionStatus | null> {
    const title = t('actions.accounting_rules.reset.title');
    const outcome = await submitTask<boolean>({
      id: makeActivityId(ActivityKind.ACCOUNTING_RULES, ActivityPart.RESET),
      kind: ActivityKind.ACCOUNTING_RULES,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<boolean, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => resetAccountingRules(),
        ),
        value => value,
      ),
      subtitle: activityLabel(ActivityKind.ACCOUNTING_RULES, ActivityPart.RESET),
      title: t('task_center.group.accounting_rules'),
    });

    if (!isErr(outcome)) {
      showSuccessMessage(title, t('actions.accounting_rules.reset.message.success'));
      return { message: '', success: outcome.value };
    }

    if (!isActionable(outcome.error))
      return null;

    showErrorMessage(title, t('actions.accounting_rules.reset.message.failure', {
      description: outcome.error.message,
    }));
    return { message: outcome.error.message, success: false };
  }

  return {
    exportJSON,
    getAccountingRule,
    getAccountingRules,
    getAccountingRulesConflicts,
    importJSON,
    resetToDefaults,
    resolveAccountingRuleConflicts,
  };
}
