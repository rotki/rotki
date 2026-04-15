import type { ActionStatus } from '@/modules/common/action';
import type {
  AddTransactionHashPayload,
  RepullingEthStakingPayload,
  RepullingEthStakingResponse,
  RepullingExchangeEventsPayload,
  RepullingExchangeEventsResponse,
  RepullingTransactionPayload,
  RepullingTransactionResponse,
} from '@/modules/history/events/event-payloads';
import type { TaskMeta } from '@/modules/tasks/types';
import { toHumanReadable } from '@rotki/common';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useRefreshTransactions } from '@/composables/history/events/tx/use-refresh-transactions';
import { displayDateFormatter } from '@/data/date-formatter';
import { ApiValidationError, type ValidationErrors } from '@/modules/api/types/errors';
import { getErrorMessage, useNotifications } from '@/modules/notifications/use-notifications';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { logger } from '@/utils/logging';

export interface RepullingTransactionResult {
  newTransactionsCount: number;
  newTransactions: Record<string, string[]>;
}

export const useHistoryTransactions = createSharedComposable(() => {
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError, notifyInfo } = useNotifications();
  const {
    addTransactionHash: addTransactionHashCaller,
    repullingEthStakingEvents: repullingEthStakingEventsCaller,
    repullingExchangeEvents: repullingExchangeEventsCaller,
    repullingTransactions: repullingTransactionsCaller,
  } = useHistoryEventsApi();

  const { runTask } = useTaskHandler();
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
    catch (error: unknown) {
      message = getErrorMessage(error);
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
    let choice: number;
    if (from && to)
      choice = 2;
    else
      choice = from ? 0 : 1;
    return t('actions.date_range', { from, to }, choice);
  };

  const repullingTransactions = async (payload: RepullingTransactionPayload): Promise<RepullingTransactionResult | undefined> => {
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

    const outcome = await runTask<RepullingTransactionResponse, TaskMeta>(
      async () => repullingTransactionsCaller(payload),
      { type: TaskType.REPULLING_TXS, meta: taskMeta, unique: false },
    );

    if (outcome.success) {
      return outcome.result;
    }
    else if (isActionableFailure(outcome)) {
      logger.error(outcome.error);
      notifyError(
        t('actions.repulling_transaction.task.title'),
        isAddressSpecified
          ? t('actions.repulling_transaction.error.description', messagePayload)
          : t('actions.repulling_transaction.error.no_address_or_chain_transaction', messagePayload),
      );
    }
    return undefined;
  };

  const repullingExchangeEvents = async (payload: RepullingExchangeEventsPayload): Promise<boolean> => {
    const dateRange = buildDateRange(payload.fromTimestamp, payload.toTimestamp);
    const messagePayload = {
      dateRange,
      exchange: `${payload.name} (${payload.location})`,
    };

    const taskMeta = {
      description: t('actions.repulling_exchange_events.task.description', messagePayload),
      title: t('actions.repulling_exchange_events.task.title'),
    };

    const outcome = await runTask<RepullingExchangeEventsResponse, TaskMeta>(
      async () => repullingExchangeEventsCaller(payload),
      { type: TaskType.REPULLING_TXS, meta: taskMeta, unique: false },
    );

    if (outcome.success) {
      const { storedEvents } = outcome.result;
      notifyInfo(
        t('actions.repulling_exchange_events.task.title'),
        storedEvents ? t('actions.repulling_exchange_events.success.description', { length: storedEvents }) : t('actions.repulling_exchange_events.success.no_events_description'),
      );

      return storedEvents > 0;
    }
    else if (isActionableFailure(outcome)) {
      logger.error(outcome.error);
      notifyError(
        t('actions.repulling_exchange_events.task.title'),
        t('actions.repulling_exchange_events.error.description', messagePayload),
      );
    }
    return false;
  };

  const repullingEthStakingEvents = async (payload: RepullingEthStakingPayload): Promise<boolean> => {
    const dateRange = buildDateRange(payload.fromTimestamp, payload.toTimestamp);
    const messagePayload = {
      dateRange,
      entryType: toHumanReadable(payload.entryType),
    };

    const taskMeta = {
      description: t('actions.repulling_eth_staking.task.description', messagePayload),
      title: t('actions.repulling_eth_staking.task.title'),
    };

    const outcome = await runTask<RepullingEthStakingResponse, TaskMeta>(
      async () => repullingEthStakingEventsCaller(payload),
      { type: TaskType.REPULLING_TXS, meta: taskMeta, unique: false },
    );

    if (outcome.success) {
      const { total, perValidator, perAddress } = outcome.result;

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

      notifyInfo(
        t('actions.repulling_eth_staking.task.title'),
        total
          ? `${t('actions.repulling_eth_staking.success.description', { ...messagePayload, count: total })}\n${details}`
          : t('actions.repulling_eth_staking.success.no_events_description', messagePayload),
      );

      return total > 0;
    }
    else if (isActionableFailure(outcome)) {
      logger.error(outcome.error);
      notifyError(
        t('actions.repulling_eth_staking.task.title'),
        t('actions.repulling_eth_staking.error.description', messagePayload),
      );
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
