import type { ResultAsync } from 'plainfp/result-async';
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
import { fromRequest, type RequestError } from '@/modules/core/api/request-result';
import { mapCollectionResponse } from '@/modules/core/common/data/collection-utils';
import { downloadFileByTextContent } from '@/modules/core/common/file/download';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import {
  accountingRulesExportActivity,
  accountingRulesImportActivity,
  accountingRulesResetActivity,
} from '@/modules/settings/accounting/accounting-rules.activity';
import { useAccountingApi } from '@/modules/settings/api/use-accounting-api';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { activityLabelOf } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseAccountingSettingsReturn {
  /**
   * The general rule for an event type, subtype and counterparty.
   *
   * @remarks
   * Carries a failure as a value, so a caller can tell "there is no such rule" (an ok `undefined`)
   * from "it could not be read", and never offers to add a rule that may already exist.
   */
  getAccountingRule: (payload: MaybeRef<AccountingRuleRequestPayload>, counterparty: string | null) => ResultAsync<AccountingRuleEntry | undefined, RequestError>;
  getAccountingRules: (payload: MaybeRef<AccountingRuleRequestPayload>) => ResultAsync<Collection<AccountingRuleEntry>, RequestError>;
  getAccountingRulesConflicts: (payload: MaybeRef<AccountingRuleConflictRequestPayload>) => ResultAsync<Collection<AccountingRuleConflict>, RequestError>;
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

  const { showErrorMessage, showSuccessMessage } = useNotifications();

  const getAccountingRule = async (
    payload: MaybeRef<AccountingRuleRequestPayload>,
    counterparty: string | null,
  ): ResultAsync<AccountingRuleEntry | undefined, RequestError> =>
    fromRequest(async () => await fetchAccountingRule(get(payload), counterparty) ?? undefined);

  const getAccountingRules = async (
    payload: MaybeRef<AccountingRuleRequestPayload>,
  ): ResultAsync<Collection<AccountingRuleEntry>, RequestError> =>
    fromRequest(async () => mapCollectionResponse(await fetchAccountingRules(get(payload))));

  const getAccountingRulesConflicts = async (
    payload: MaybeRef<AccountingRuleConflictRequestPayload>,
  ): ResultAsync<Collection<AccountingRuleConflict>, RequestError> =>
    fromRequest(async () => mapCollectionResponse(await fetchAccountingRuleConflicts(get(payload))));

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

  /**
   * Runs the export as a task.
   *
   * @returns null when the task did not finish: its row in the task centre reports why
   */
  const exportAccountingRulesData = async (
    directoryPath?: string,
  ): Promise<boolean | object | null> => {
    const outcome = await submitTask<boolean | object>({
      id: accountingRulesExportActivity.id(),
      kind: accountingRulesExportActivity.kind,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<boolean | object, TaskError>> => mapResult(
        await runTask<boolean | object>(
          async () => exportAccountingRules(directoryPath),
        ),
        value => value,
      ),
      subtitle: activityLabelOf(accountingRulesExportActivity),
      title: t('task_center.group.accounting_rules'),
    });

    return isErr(outcome) ? null : outcome.value;
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

      const result = await exportAccountingRulesData(directoryPath);
      if (result === null)
        return;

      if (appSession) {
        showSuccessMessage(title, t('actions.accounting_rules.export.message.success'));
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
      id: accountingRulesImportActivity.id(),
      kind: accountingRulesImportActivity.kind,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<boolean, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => path ? importAccountingRulesData(path) : uploadAccountingRulesData(file),
        ),
        value => value,
      ),
      subtitle: activityLabelOf(accountingRulesImportActivity, { file: file.name }),
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
      id: accountingRulesResetActivity.id(),
      kind: accountingRulesResetActivity.kind,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<boolean, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => resetAccountingRules(),
        ),
        value => value,
      ),
      subtitle: activityLabelOf(accountingRulesResetActivity),
      title: t('task_center.group.accounting_rules'),
    });

    if (!isErr(outcome)) {
      showSuccessMessage(title, t('actions.accounting_rules.reset.message.success'));
      return { message: '', success: outcome.value };
    }

    if (!isActionable(outcome.error))
      return null;

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
