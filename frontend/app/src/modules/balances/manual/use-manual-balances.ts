import type { ActionStatus } from '@/types/action';
import type { TaskMeta } from '@/types/task';
import { useManualBalancesApi } from '@/composables/api/balances/manual';
import { useStatusUpdater } from '@/composables/status';
import { useUsdValueThreshold } from '@/composables/usd-value-threshold';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useMessageStore } from '@/store/message';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import { BalanceType } from '@/types/balances';
import {
  type ManualBalance,
  ManualBalances,
  type ManualBalanceWithValue,
  type RawManualBalance,
} from '@/types/manual-balances';
import { BalanceSource } from '@/types/settings/frontend-settings';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { logger } from '@/utils/logging';

interface UseManualBalancesReturn {
  addManualBalance: (balance: RawManualBalance) => Promise<ActionStatus<ValidationErrors | string>>;
  deleteManualBalance: (id: number) => Promise<void>;
  editManualBalance: (balance: ManualBalance) => Promise<ActionStatus<ValidationErrors | string>>;
  fetchManualBalances: (userInitiated?: boolean) => Promise<void>;
  save: (balance: ManualBalance | RawManualBalance) => Promise<ActionStatus<ValidationErrors | string>>;
}

export function useManualBalances(): UseManualBalancesReturn {
  const { manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());
  const { notify } = useNotificationsStore();
  const { setMessage } = useMessageStore();
  const { awaitTask } = useTaskStore();
  const { fetchDisabled, getStatus, resetStatus, setStatus } = useStatusUpdater(Section.MANUAL_BALANCES);
  const { addManualBalances, deleteManualBalances, editManualBalances, queryManualBalances } = useManualBalancesApi();
  const usdValueThreshold = useUsdValueThreshold(BalanceSource.MANUAL);
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

    const threshold = get(usdValueThreshold);

    try {
      const taskType = TaskType.MANUAL_BALANCES;
      const { taskId } = await queryManualBalances(threshold);
      const { result } = await awaitTask<ManualBalances, TaskMeta>(taskId, taskType, {
        title: t('actions.manual_balances.fetch.task.title'),
      });

      const { balances } = ManualBalances.parse(result);
      updateBalances(balances);

      setStatus(Status.LOADED);
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        notify({
          display: true,
          message: t('actions.balances.manual_balances.error.message', {
            message: error.message,
          }),
          title: t('actions.balances.manual_balances.error.title'),
        });
      }
      resetStatus();
    }
  };

  const addManualBalance = async (balance: RawManualBalance): Promise<ActionStatus<ValidationErrors | string>> => {
    try {
      const taskType = TaskType.MANUAL_BALANCES_ADD;
      const { taskId } = await addManualBalances([balance]);
      const { result } = await awaitTask<ManualBalances, TaskMeta>(taskId, taskType, {
        title: t('actions.manual_balances.add.task.title'),
      });
      const { balances } = ManualBalances.parse(result);
      updateBalances(balances);
      return {
        success: true,
      };
    }
    catch (error: any) {
      if (!isTaskCancelled(error))
        logger.error(error);

      let messages = error.message;
      if (error instanceof ApiValidationError)
        messages = error.getValidationErrors(balance);

      return {
        message: messages,
        success: false,
      };
    }
  };

  const editManualBalance = async (balance: ManualBalance): Promise<ActionStatus<ValidationErrors | string>> => {
    try {
      const taskType = TaskType.MANUAL_BALANCES_EDIT;
      const { taskId } = await editManualBalances([balance]);
      const { result } = await awaitTask<ManualBalances, TaskMeta>(taskId, taskType, {
        title: t('actions.manual_balances.edit.task.title'),
      });
      const { balances } = ManualBalances.parse(result);
      updateBalances(balances);
      return {
        success: true,
      };
    }
    catch (error: any) {
      if (!isTaskCancelled(error))
        logger.error(error);

      let message = error.message;
      if (error instanceof ApiValidationError)
        message = error.getValidationErrors(balance);

      return {
        message,
        success: false,
      };
    }
  };

  const save = async (balance: ManualBalance | RawManualBalance): Promise<ActionStatus<ValidationErrors | string>> =>
    'identifier' in balance ? editManualBalance(balance) : addManualBalance(balance);

  const deleteManualBalance = async (id: number): Promise<void> => {
    try {
      const { balances } = await deleteManualBalances([id]);
      updateBalances(balances);
    }
    catch (error: any) {
      setMessage({
        description: error.message,
        title: t('actions.balances.manual_delete.error.title'),
      });
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
