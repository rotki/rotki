import type { ActionStatus } from '@/modules/core/common/action';
import type { ActivityId, ActivityKind } from '@/modules/task-center/core/types';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { useValueThreshold } from '@/modules/assets/amount-display/use-usd-value-threshold';
import { useManualBalancesApi } from '@/modules/balances/api/use-manual-balances-api';
import {
  manualBalanceAddActivity,
  manualBalanceEditActivity,
  manualBalancesFetchActivity,
} from '@/modules/balances/balances.activity';
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
import { shouldSkipFetch } from '@/modules/task-center/core/status';
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
  const { showErrorMessage } = useNotifications();
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
    const status = statusOf(manualBalancesFetchActivity.kind, ...manualBalancesFetchActivity.partsOf());
    if (shouldSkipFetch(status, userInitiated)) {
      logger.debug('skipping manual balance refresh');
      return;
    }

    const threshold = get(valueThreshold);

    const outcome = await submitTask({
      id: manualBalancesFetchActivity.id(),
      kind: manualBalancesFetchActivity.kind,
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

    onActionableError(outcome, error => logger.error(error.message));
  };

  /**
   * Add and edit differ only in identity and endpoint, so they share one submission. The identity
   * comes from {@link manualBalanceAddActivity} or {@link manualBalanceEditActivity}, which key it
   * by the balance.
   */
  async function saveManualBalance<T extends ManualBalance | RawManualBalance>(
    balance: T,
    activity: { readonly id: ActivityId; readonly kind: ActivityKind },
    apiCall: () => Promise<{ taskId: number }>,
  ): Promise<ActionStatus<ValidationErrors | string>> {
    cancelActivity(manualBalancesFetchActivity.kind, ...manualBalancesFetchActivity.partsOf());

    const outcome = await submitTask({
      id: activity.id,
      kind: activity.kind,
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
      { id: manualBalanceAddActivity.id(balance), kind: manualBalanceAddActivity.kind },
      async () => addManualBalances([balance]),
    );

  const editManualBalance = async (balance: ManualBalance): Promise<ActionStatus<ValidationErrors | string>> =>
    saveManualBalance(
      balance,
      { id: manualBalanceEditActivity.id(balance), kind: manualBalanceEditActivity.kind },
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
