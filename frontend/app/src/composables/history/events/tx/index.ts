import type { ActionStatus } from '@/types/action';
import type {
  AddTransactionHashPayload,
  RepullingExchangeEventsPayload,
  RepullingExchangeEventsResponse,
  RepullingTransactionPayload,
  RepullingTransactionResponse,
} from '@/types/history/events';
import type { TaskMeta } from '@/types/task';
import { Severity, toHumanReadable } from '@rotki/common';
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

export const useHistoryTransactions = createSharedComposable(() => {
  const { t } = useI18n({ useScope: 'global' });
  const { notify } = useNotificationsStore();
  const {
    addTransactionHash: addTransactionHashCaller,
    repullingExchangeEvents: repullingExchangeEventsCaller,
    repullingTransactions: repullingTransactionsCaller,
  } = useHistoryEventsApi();

  const { awaitTask } = useTaskStore();
  const { dateDisplayFormat } = storeToRefs(useGeneralSettingsStore());
  const { refreshTransactions } = useRefreshTransactions();

  const formatTimestamp = (seconds: number): string =>
    displayDateFormatter.format(new Date(seconds * 1000), get(dateDisplayFormat));

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

  const repullingTransactions = async (payload: RepullingTransactionPayload): Promise<boolean> => {
    const taskType = TaskType.REPULLING_TXS;
    const { taskId } = await repullingTransactionsCaller(payload);

    const messagePayload = {
      address: payload.address,
      chain: payload.chain ? toHumanReadable(payload.chain) : undefined,
      from: formatTimestamp(payload.fromTimestamp),
      to: formatTimestamp(payload.toTimestamp),
    };

    const isAddressSpecified = payload.address && payload.chain;

    const taskMeta = {
      description: isAddressSpecified
        ? t('actions.repulling_transaction.task.description', messagePayload)
        : t('actions.repulling_transaction.task.no_address_or_chain_transaction', messagePayload),
      title: t('actions.repulling_transaction.task.title'),
    };

    try {
      const { result } = await awaitTask<RepullingTransactionResponse, TaskMeta>(taskId, taskType, taskMeta, true);
      const { newTransactionsCount } = result;
      notify({
        display: true,
        message: newTransactionsCount ? t('actions.repulling_transaction.success.description', { length: newTransactionsCount }) : t('actions.repulling_transaction.success.no_tx_description'),
        severity: Severity.INFO,
        title: t('actions.repulling_transaction.task.title'),
      });

      return newTransactionsCount > 0;
    }
    catch (error: any) {
      if (isTaskCancelled(error)) {
        return false;
      }
      logger.error(error);
      notify({
        display: true,
        message: isAddressSpecified
          ? t('actions.repulling_transaction.error.description', messagePayload)
          : t('actions.repulling_transaction.error.no_address_or_chain_transaction', messagePayload),
        title: t('actions.repulling_transaction.task.title'),
      });
    }
    return false;
  };

  const repullingExchangeEvents = async (payload: RepullingExchangeEventsPayload): Promise<boolean> => {
    const taskType = TaskType.REPULLING_TXS;
    const { taskId } = await repullingExchangeEventsCaller(payload);

    const messagePayload = {
      exchange: `${payload.name} (${payload.location})`,
      from: formatTimestamp(payload.fromTimestamp),
      to: formatTimestamp(payload.toTimestamp),
    };

    const taskMeta = {
      description: t('actions.repulling_exchange_events.task.description', messagePayload),
      title: t('actions.repulling_exchange_events.task.title'),
    };

    try {
      const { result } = await awaitTask<RepullingExchangeEventsResponse, TaskMeta>(taskId, taskType, taskMeta, true);
      const { storedEvents } = result;
      notify({
        display: true,
        message: storedEvents ? t('actions.repulling_exchange_events.success.description', { length: storedEvents }) : t('actions.repulling_exchange_events.success.no_events_description'),
        severity: Severity.INFO,
        title: t('actions.repulling_exchange_events.task.title'),
      });

      return storedEvents > 0;
    }
    catch (error: any) {
      if (isTaskCancelled(error)) {
        return false;
      }
      logger.error(error);
      notify({
        display: true,
        message: t('actions.repulling_exchange_events.error.description', messagePayload),
        title: t('actions.repulling_exchange_events.task.title'),
      });
    }
    return false;
  };

  return {
    addTransactionHash,
    refreshTransactions,
    repullingExchangeEvents,
    repullingTransactions,
  };
});
