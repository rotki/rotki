import type { ActionStatus } from '@/modules/core/common/action';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
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
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

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
  const { cancelActivity, statusOf, submitTask } = useNativeTask();
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
    // `fetchDisabled(refresh)` was `!(isFirstLoad || refresh) || loading`; on the orchestrator's
    // projection that is `(everCompleted && !userInitiated) || active`.
    const status = statusOf(ActivityKind.MANUAL_BALANCES, ActivityPart.FETCH);
    if ((status.everCompleted && !userInitiated) || status.active) {
      logger.debug('skipping manual balance refresh');
      return;
    }

    const threshold = get(valueThreshold);

    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.MANUAL_BALANCES, ActivityPart.FETCH),
      kind: ActivityKind.MANUAL_BALANCES,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<ManualBalances>(
          async () => queryManualBalances(threshold),
        ),
        (result) => {
          updateBalances(ManualBalances.parse(result).balances);
        },
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.manual_balances.fetch')),
      title: t('task_center.group.manual_balances'),
    });

    onActionableError(outcome, (error) => {
      logger.error(error.message);
      notifyError(
        t('actions.balances.manual_balances.error.title'),
        t('actions.balances.manual_balances.error.message', { message: error.message }),
      );
    });
  };

  /**
   * Add and edit differ only in task type, part, endpoint and identity, so they share one
   * submission. The id carries the balance's identity (`identifier` for edit, location+asset+label
   * for add) rather than being a per-part singleton: `submitTask` dedups by id, so a shared id
   * would hand two concurrent saves the same promise and report one the other's outcome.
   */
  async function saveManualBalance<T extends ManualBalance | RawManualBalance>(
    balance: T,
    part: ActivityPart,
    identity: (string | number)[],
    title: string,
    apiCall: () => Promise<{ taskId: number }>,
  ): Promise<ActionStatus<ValidationErrors | string>> {
    // A save supersedes an in-flight list refresh, which would otherwise clobber the new data.
    // Cancelling by activity (not by task type) settles the FETCH activity terminal right away:
    // the backend routinely refuses the abort, and the old `cancelTaskByTaskType` left nothing to
    // settle the native activity, so its `active` status — and every spinner reading it — stayed
    // stuck until the monitor reaped the task ~30s later.
    cancelActivity(ActivityKind.MANUAL_BALANCES, ActivityPart.FETCH);

    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.MANUAL_BALANCES, part, ...identity),
      kind: ActivityKind.MANUAL_BALANCES,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<ManualBalances>(apiCall),
        (result) => {
          updateBalances(ManualBalances.parse(result).balances);
        },
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.manual_balances.save'), { label: balance.label }),
      title: t('task_center.group.manual_balances'),
    });

    if (!isErr(outcome))
      return { success: true };

    if (!isActionable(outcome.error))
      return { message: '', success: false };

    logger.error(outcome.error.message);

    // The backend's field-level validation errors ride on the tagged error's `cause`.
    const cause = outcome.error.cause;
    const message: ValidationErrors | string = cause instanceof ApiValidationError
      ? cause.getValidationErrors(balance)
      : outcome.error.message;

    return { message, success: false };
  }

  const addManualBalance = async (balance: RawManualBalance): Promise<ActionStatus<ValidationErrors | string>> =>
    saveManualBalance(
      balance,
      ActivityPart.ADD,
      [balance.location, balance.asset, balance.label],
      t('actions.manual_balances.add.task.title'),
      async () => addManualBalances([balance]),
    );

  const editManualBalance = async (balance: ManualBalance): Promise<ActionStatus<ValidationErrors | string>> =>
    saveManualBalance(
      balance,
      ActivityPart.EDIT,
      [balance.identifier],
      t('actions.manual_balances.edit.task.title'),
      async () => editManualBalances([balance]),
    );

  const save = async (balance: ManualBalance | RawManualBalance): Promise<ActionStatus<ValidationErrors | string>> =>
    'identifier' in balance ? editManualBalance(balance) : addManualBalance(balance);

  const deleteManualBalance = async (id: number): Promise<void> => {
    try {
      const { balances } = await deleteManualBalances([id]);
      updateBalances(balances);
    }
    catch (error: unknown) {
      if (isRequestCancellation(error))
        return;

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
