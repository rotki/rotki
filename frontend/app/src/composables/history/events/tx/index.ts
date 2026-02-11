import type { ActionStatus } from '@/types/action';
import type {
  AddTransactionHashPayload,
  RepullingEthStakingPayload,
  RepullingEthStakingResponse,
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

export interface RepullingTransactionResult {
  newTransactionsCount: number;
  newTransactions: Record<string, string[]>;
}

export const useHistoryTransactions = createSharedComposable(() => {
  const { t } = useI18n({ useScope: 'global' });
  const { notify } = useNotificationsStore();
  const {
    addTransactionHash: addTransactionHashCaller,
    repullingEthStakingEvents: repullingEthStakingEventsCaller,
    repullingExchangeEvents: repullingExchangeEventsCaller,
    repullingTransactions: repullingTransactionsCaller,
  } = useHistoryEventsApi();

  const { awaitTask } = useTaskStore();
  const { dateDisplayFormat } = storeToRefs(useGeneralSettingsStore());
  const { refreshTransactions } = useRefreshTransactions();

  const formatTimestamp = (seconds: number | undefined): string | undefined => {
    if (seconds === undefined)
      return undefined;

    return displayDateFormatter.format(new Date(seconds * 1000), get(dateDisplayFormat));
  };

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

  const buildDateRange = (fromTimestamp?: number, toTimestamp?: number): string => {
    const from = formatTimestamp(fromTimestamp);
    const to = formatTimestamp(toTimestamp);

    if (!to && !from)
      return '';

    // 0 = only from, 1 = only to, 2 = both
    const choice = from && to ? 2 : (from ? 0 : 1);
    return t('actions.date_range', { from, to }, choice);
  };

  const repullingTransactions = async (payload: RepullingTransactionPayload): Promise<RepullingTransactionResult | undefined> => {
    const taskType = TaskType.REPULLING_TXS;
    const { taskId } = await repullingTransactionsCaller(payload);

    const dateRange = buildDateRange(payload.fromTimestamp, payload.toTimestamp);
    const messagePayload = {
      address: payload.address,
      chain: payload.chain ? toHumanReadable(payload.chain) : undefined,
      dateRange,
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
      return result;
    }
    catch (error: any) {
      if (isTaskCancelled(error)) {
        return undefined;
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
    return undefined;
  };

  const repullingExchangeEvents = async (payload: RepullingExchangeEventsPayload): Promise<boolean> => {
    const taskType = TaskType.REPULLING_TXS;
    const { taskId } = await repullingExchangeEventsCaller(payload);

    const dateRange = buildDateRange(payload.fromTimestamp, payload.toTimestamp);
    const messagePayload = {
      dateRange,
      exchange: `${payload.name} (${payload.location})`,
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

  const repullingEthStakingEvents = async (payload: RepullingEthStakingPayload): Promise<boolean> => {
    const taskType = TaskType.REPULLING_TXS;
    const { taskId } = await repullingEthStakingEventsCaller(payload);

    const dateRange = buildDateRange(payload.fromTimestamp, payload.toTimestamp);
    const messagePayload = {
      dateRange,
      entryType: toHumanReadable(payload.entryType),
    };

    const taskMeta = {
      description: t('actions.repulling_eth_staking.task.description', messagePayload),
      title: t('actions.repulling_eth_staking.task.title'),
    };

    try {
      const { result } = await awaitTask<RepullingEthStakingResponse, TaskMeta>(taskId, taskType, taskMeta, true);
      const { total, perValidator, perAddress } = result;

      const validatorDetails = Object.entries(perValidator)
        .map(([index, count]) => `  ${t('actions.repulling_eth_staking.success.validator_entry', { index, count })}`)
        .join('\n');

      const addressDetails = Object.entries(perAddress)
        .map(([address, count]) => `  ${t('actions.repulling_eth_staking.success.address_entry', { address, count })}`)
        .join('\n');

      const details = [
        validatorDetails ? `${t('actions.repulling_eth_staking.success.per_validator')}:\n${validatorDetails}` : '',
        addressDetails ? `${t('actions.repulling_eth_staking.success.per_address')}:\n${addressDetails}` : '',
      ].filter(Boolean).join('\n\n');

      notify({
        display: true,
        message: total
          ? `${t('actions.repulling_eth_staking.success.description', { ...messagePayload, count: total })}\n${details}`
          : t('actions.repulling_eth_staking.success.no_events_description', messagePayload),
        severity: Severity.INFO,
        title: t('actions.repulling_eth_staking.task.title'),
      });

      return total > 0;
    }
    catch (error: any) {
      if (isTaskCancelled(error)) {
        return false;
      }
      logger.error(error);
      notify({
        display: true,
        message: t('actions.repulling_eth_staking.error.description', messagePayload),
        title: t('actions.repulling_eth_staking.task.title'),
      });
    }
    return false;
  };

  return {
    addTransactionHash,
    refreshTransactions,
    repullingEthStakingEvents,
    repullingExchangeEvents,
    repullingTransactions,
  };
});
