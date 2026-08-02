import type { ActionStatus } from '@/modules/core/common/action';
import type {
  AddTransactionHashPayload,
  RepullingEthStakingPayload,
  RepullingEthStakingResponse,
  RepullingExchangeEventsPayload,
  RepullingExchangeEventsResponse,
  RepullingTransactionPayload,
  RepullingTransactionResponse,
} from '@/modules/history/events/event-payloads';
import { toHumanReadable } from '@rotki/common';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { displayDateFormatter } from '@/modules/core/common/date-formatter';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { useRefreshTransactions } from '@/modules/history/events/tx/use-refresh-transactions';
import { useSetting } from '@/modules/settings/use-setting';
import { type ActivityId, ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

export interface RepullingTransactionResult {
  newTransactionsCount: number;
  newTransactions: Record<string, string[]>;
}

/**
 * The identity of one transaction re-pull.
 *
 * Extracted rather than inlined: every optional field needs its own fallback, and those branches
 * pushed `repullingTransactions` past the complexity cap. An absent bound is still part of the
 * identity — "everything before X" is a different request from "X to Y".
 */
function repullTransactionsActivityId(payload: RepullingTransactionPayload): ActivityId {
  return makeActivityId(
    ActivityKind.REPULLING,
    ActivityPart.TRANSACTIONS,
    payload.address ?? '',
    payload.chain ?? '',
    payload.fromTimestamp ?? 0,
    payload.toTimestamp ?? 0,
  );
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

  const { submitTask } = useNativeTask();
  const dateDisplayFormat = useSetting('dateDisplayFormat');
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

    const subtitle = isAddressSpecified
      ? t('actions.repulling_transaction.task.description', messagePayload)
      : t('actions.repulling_transaction.task.no_address_or_chain_transaction', messagePayload);

    // The operation *and* its payload are the identity. `REPULLING` covers three unrelated backend
    // calls, and all three submitted under the bare kind: a second re-pull of any of them started
    // while another was live was deduped onto it and returned "no new events" without doing any
    // work, and cancelling "repulling" killed whichever of the three happened to own the record.
    const outcome = await submitTask<RepullingTransactionResponse | undefined>({
      id: repullTransactionsActivityId(payload),
      kind: ActivityKind.REPULLING,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<RepullingTransactionResponse | undefined, TaskError>> => mapResult(
        await runTask<RepullingTransactionResponse>(
          async () => repullingTransactionsCaller(payload),
        ),
        value => value,
      ),
      subtitle,
      title: t('task_center.group.repulling'),
    });

    if (!isErr(outcome)) {
      return outcome.value;
    }
    if (isActionable(outcome.error)) {
      logger.error(outcome.error.message);
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

    const subtitle = t('actions.repulling_exchange_events.task.description', messagePayload);

    const outcome = await submitTask<RepullingExchangeEventsResponse>({
      id: makeActivityId(
        ActivityKind.REPULLING,
        ActivityPart.EXCHANGE_EVENTS,
        payload.location,
        payload.name,
        payload.fromTimestamp ?? 0,
        payload.toTimestamp ?? 0,
      ),
      kind: ActivityKind.REPULLING,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<RepullingExchangeEventsResponse, TaskError>> => mapResult(
        await runTask<RepullingExchangeEventsResponse>(
          async () => repullingExchangeEventsCaller(payload),
        ),
        value => value,
      ),
      subtitle,
      title: t('task_center.group.repulling'),
    });

    if (!isErr(outcome)) {
      const { storedEvents } = outcome.value;
      notifyInfo(
        t('actions.repulling_exchange_events.task.title'),
        storedEvents ? t('actions.repulling_exchange_events.success.description', { length: storedEvents }) : t('actions.repulling_exchange_events.success.no_events_description'),
      );

      return storedEvents > 0;
    }
    if (isErr(outcome) && isActionable(outcome.error)) {
      logger.error(outcome.error.message);
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

    const subtitle = t('actions.repulling_eth_staking.task.description', messagePayload);

    const outcome = await submitTask<RepullingEthStakingResponse>({
      id: makeActivityId(
        ActivityKind.REPULLING,
        ActivityPart.STAKING,
        payload.entryType,
        payload.fromTimestamp ?? 0,
        payload.toTimestamp ?? 0,
      ),
      kind: ActivityKind.REPULLING,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<RepullingEthStakingResponse, TaskError>> => mapResult(
        await runTask<RepullingEthStakingResponse>(
          async () => repullingEthStakingEventsCaller(payload),
        ),
        value => value,
      ),
      subtitle,
      title: t('task_center.group.repulling'),
    });

    if (!isErr(outcome)) {
      const { total, perValidator, perAddress } = outcome.value;

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
    if (isErr(outcome) && isActionable(outcome.error)) {
      logger.error(outcome.error.message);
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
