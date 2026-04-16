import type { ActionStatus } from '@/modules/core/common/action';
import type { TaskMeta } from '@/modules/core/tasks/types';
import { useValueThreshold } from '@/modules/assets/amount-display/use-usd-value-threshold';
import { useManualBalancesApi } from '@/modules/balances/api/use-manual-balances-api';
import { BalanceType } from '@/modules/balances/types/balances';
import {
  type ManualBalance,
  ManualBalances,
  type ManualBalanceWithValue,
  type RawManualBalance,
} from '@/modules/balances/types/manual-balances';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { Section, Status } from '@/modules/core/common/status';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';
import { useStatusUpdater } from '@/modules/shell/sync-progress/use-status-updater';

interface UseManualBalancesReturn {
  addManualBalance: (balance: RawManualBalance) => Promise<ActionStatus<ValidationErrors | string>>;
  deleteManualBalance: (id: number) => Promise<void>;
  editManualBalance: (balance: ManualBalance) => Promise<ActionStatus<ValidationErrors | string>>;
  fetchManualBalances: (userInitiated?: boolean) => Promise<void>;
  save: (balance: ManualBalance | RawManualBalance) => Promise<ActionStatus<ValidationErrors | string>>;
}

export function useManualBalances(): UseManualBalancesReturn {
  const { manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());
  const { notifyError, showErrorMessage } = useNotifications();
  const { cancelTaskByTaskType, runTask } = useTaskHandler();
  const { fetchDisabled, getStatus, resetStatus, setStatus } = useStatusUpdater(Section.MANUAL_BALANCES);
  const { addManualBalances, deleteManualBalances, editManualBalances, queryManualBalances } = useManualBalancesApi();
  const valueThreshold = useValueThreshold(BalanceSource.MANUAL);
  const { t } = useI18n({ useScope: 'global' });

  function updateBalances(balances: ManualBalanceWithValue[]): void {
    const assets: ManualBalanceWithValue[] = [];
    const liabilities: ManualBalanceWithValue[] = [];

    for (const balance of balances) {
      if (balance.balanceType === BalanceType.LIABILITY) {
        liabilities.push(balance);
      }
      else {
        assets.push(balance);
      }
    }

    set(manualBalances, assets);
    set(manualLiabilities, liabilities);
  }

  const fetchManualBalances = async (userInitiated = false): Promise<void> => {
    if (fetchDisabled(userInitiated)) {
      logger.debug('skipping manual balance refresh');
      return;
    }
    const currentStatus: Status = getStatus();

    const newStatus = currentStatus === Status.LOADED ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus);

    const threshold = get(valueThreshold);

    const outcome = await runTask<ManualBalances, TaskMeta>(
      async () => queryManualBalances(threshold),
      { type: TaskType.MANUAL_BALANCES, meta: { title: t('actions.manual_balances.fetch.task.title') } },
    );

    if (outcome.success) {
      const { balances } = ManualBalances.parse(outcome.result);
      updateBalances(balances);
      setStatus(Status.LOADED);
    }
    else {
      if (isActionableFailure(outcome)) {
        logger.error(outcome.error);
        notifyError(
          t('actions.balances.manual_balances.error.title'),
          t('actions.balances.manual_balances.error.message', { message: outcome.message }),
        );
      }
      resetStatus();
    }
  };

  const addManualBalance = async (balance: RawManualBalance): Promise<ActionStatus<ValidationErrors | string>> => {
    await cancelTaskByTaskType(TaskType.MANUAL_BALANCES);
    const outcome = await runTask<ManualBalances, TaskMeta>(
      async () => addManualBalances([balance]),
      { type: TaskType.MANUAL_BALANCES_ADD, meta: { title: t('actions.manual_balances.add.task.title') } },
    );

    if (outcome.success) {
      const { balances } = ManualBalances.parse(outcome.result);
      updateBalances(balances);
      return { success: true };
    }

    if (isActionableFailure(outcome)) {
      logger.error(outcome.error);

      let messages: ValidationErrors | string = outcome.message;
      if (outcome.error instanceof ApiValidationError)
        messages = outcome.error.getValidationErrors(balance);

      return {
        message: messages,
        success: false,
      };
    }

    return { message: '', success: false };
  };

  const editManualBalance = async (balance: ManualBalance): Promise<ActionStatus<ValidationErrors | string>> => {
    await cancelTaskByTaskType(TaskType.MANUAL_BALANCES);
    const outcome = await runTask<ManualBalances, TaskMeta>(
      async () => editManualBalances([balance]),
      { type: TaskType.MANUAL_BALANCES_EDIT, meta: { title: t('actions.manual_balances.edit.task.title') } },
    );

    if (outcome.success) {
      const { balances } = ManualBalances.parse(outcome.result);
      updateBalances(balances);
      return { success: true };
    }

    if (isActionableFailure(outcome)) {
      logger.error(outcome.error);

      let message: ValidationErrors | string = outcome.message;
      if (outcome.error instanceof ApiValidationError)
        message = outcome.error.getValidationErrors(balance);

      return {
        message,
        success: false,
      };
    }

    return { message: '', success: false };
  };

  const save = async (balance: ManualBalance | RawManualBalance): Promise<ActionStatus<ValidationErrors | string>> =>
    'identifier' in balance ? editManualBalance(balance) : addManualBalance(balance);

  const deleteManualBalance = async (id: number): Promise<void> => {
    try {
      const { balances } = await deleteManualBalances([id]);
      updateBalances(balances);
    }
    catch (error: unknown) {
      showErrorMessage(t('actions.balances.manual_delete.error.title'), getErrorMessage(error));
    }
  };

  return {
    addManualBalance,
    deleteManualBalance,
    editManualBalance,
    fetchManualBalances,
    save,
  };
}
