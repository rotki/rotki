import type { ActionStatus } from '@/types/action';
import type {
  AddTransactionHashPayload,
  RepullingTransactionPayload,
  RepullingTransactionResponse,
} from '@/types/history/events';
import type { TaskMeta } from '@/types/task';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useRefreshTransactions } from '@/composables/history/events/tx/use-refresh-transactions';
import { displayDateFormatter } from '@/data/date-formatter';
import { useNotificationsStore } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTaskStore } from '@/store/tasks';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { logger } from '@/utils/logging';
import { Severity, toHumanReadable } from '@rotki/common';
import { startPromise } from '@shared/utils';

export const useHistoryTransactions = createSharedComposable(() => {
  const { t } = useI18n({ useScope: 'global' });
  const { notify } = useNotificationsStore();
  const {
    addTransactionHash: addTransactionHashCaller,
    repullingTransactions: repullingTransactionsCaller,
  } = useHistoryEventsApi();

  const { awaitTask } = useTaskStore();
  const { dateDisplayFormat } = storeToRefs(useGeneralSettingsStore());
  const { refreshTransactions } = useRefreshTransactions();

  const addTransactionHash = async (payload: AddTransactionHashPayload): Promise<ActionStatus<ValidationErrors | string>> => {
    let success = false;
    let message: ValidationErrors | string = '';
    try {
      await addTransactionHashCaller(payload);
      success = true;
    }
    catch (error: any) {
      message = error.message;
      if (error instanceof ApiValidationError) {
        message = error.getValidationErrors(payload);
      }
    }

    return { message, success };
  };

  const repullingTransactions = async (payload: RepullingTransactionPayload, refresh: () => void): Promise<void> => {
    const taskType = TaskType.REPULLING_TXS;
    const { taskId } = await repullingTransactionsCaller(payload);

    const messagePayload = {
      address: payload.address,
      chain: payload.evmChain ? toHumanReadable(payload.evmChain) : undefined,
      from: displayDateFormatter.format(new Date(payload.fromTimestamp * 1000), get(dateDisplayFormat)),
      to: displayDateFormatter.format(new Date(payload.toTimestamp * 1000), get(dateDisplayFormat)),
    };

    const isAddressSpecified = payload.address && payload.evmChain;

    const taskMeta = {
      description: isAddressSpecified
        ? t('actions.repulling_transaction.task.description', messagePayload)
        : t('actions.repulling_transaction.task.no_address_or_chain_transaction', messagePayload),
      title: t('actions.repulling_transaction.task.title'),
    };

    const taskFunc = async (): Promise<void> => {
      try {
        const { result } = await awaitTask<RepullingTransactionResponse, TaskMeta>(taskId, taskType, taskMeta, true);
        const { newTransactionsCount } = result;
        notify({
          display: true,
          message: newTransactionsCount ? t('actions.repulling_transaction.success.description', { length: newTransactionsCount }) : t('actions.repulling_transaction.success.no_tx_description'),
          severity: Severity.INFO,
          title: t('actions.repulling_transaction.task.title'),
        });
        if (newTransactionsCount) {
          refresh();
        }
      }
      catch (error: any) {
        if (!isTaskCancelled(error)) {
          logger.error(error);
          notify({
            display: true,
            message: isAddressSpecified
              ? t('actions.repulling_transaction.error.description', messagePayload)
              : t('actions.repulling_transaction.error.no_address_or_chain_transaction', messagePayload),
            title: t('actions.repulling_transaction.task.title'),
          });
        }
      }
    };

    startPromise(taskFunc());
  };

  return {
    addTransactionHash,
    refreshTransactions,
    repullingTransactions,
  };
});
