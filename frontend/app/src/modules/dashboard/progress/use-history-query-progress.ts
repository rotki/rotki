import type { ComputedRef } from 'vue';
import type { CommonQueryProgressData, HistoryQueryProgressType } from '@/modules/dashboard/progress/types';
import { get } from '@vueuse/shared';
import {
  type HistoryEventsQueryData,
  HistoryEventsQueryStatus,
  TransactionsQueryStatus,
} from '@/modules/core/messaging/types';
import { useSyncRollup } from '@/modules/history/events/tx/use-sync-rollup';
import { useEventsQueryStatusStore } from '@/modules/history/use-events-query-status-store';
import { isTxQueryStatusFinished, type TxQueryStatusData, useTxQueryStatusStore } from '@/modules/history/use-tx-query-status-store';

interface HistoryQueryProgressOperationData {
  type: HistoryQueryProgressType;
  address?: string;
  chain?: string;
  location?: string;
  name?: string;
  status: string;
}

export interface HistoryQueryProgress extends CommonQueryProgressData<HistoryQueryProgressOperationData> {}

interface UseHistoryQueryProgressReturn {
  progress: ComputedRef<HistoryQueryProgress | undefined>;
}

function getTransactionStatusDescription(status: TransactionsQueryStatus, t: ReturnType<typeof useI18n>['t']): string {
  const statusDescriptions: Record<TransactionsQueryStatus, string> = {
    [TransactionsQueryStatus.ACCOUNT_CHANGE]: t('dashboard.history_query_indicator.transaction_status.querying_transactions_started'),
    [TransactionsQueryStatus.CANCELLED]: t('dashboard.history_query_indicator.transaction_status.cancelled'),
    [TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED]: t('dashboard.history_query_indicator.transaction_status.decoding_transactions_finished'),
    [TransactionsQueryStatus.DECODING_TRANSACTIONS_STARTED]: t('dashboard.history_query_indicator.transaction_status.decoding_transactions_started'),
    [TransactionsQueryStatus.FAILED]: t('dashboard.history_query_indicator.transaction_status.failed'),
    [TransactionsQueryStatus.QUERYING_EVM_TOKENS_TRANSACTIONS]: t('dashboard.history_query_indicator.transaction_status.querying_evm_tokens_transactions'),
    [TransactionsQueryStatus.QUERYING_INTERNAL_TRANSACTIONS]: t('dashboard.history_query_indicator.transaction_status.querying_internal_transactions'),
    [TransactionsQueryStatus.QUERYING_TRANSACTIONS]: t('dashboard.history_query_indicator.transaction_status.querying_transactions'),
    [TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED]: t('dashboard.history_query_indicator.transaction_status.querying_transactions_finished'),
    [TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED]: t('dashboard.history_query_indicator.transaction_status.querying_transactions_started'),
  };

  return statusDescriptions[status] || t('dashboard.history_query_indicator.transaction_status.default');
}

function getEventStatusDescription(status: HistoryEventsQueryStatus, t: ReturnType<typeof useI18n>['t']): string {
  const statusDescriptions: Record<HistoryEventsQueryStatus, string> = {
    [HistoryEventsQueryStatus.CANCELLED]: t('dashboard.history_query_indicator.event_status.cancelled'),
    [HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED]: t('dashboard.history_query_indicator.event_status.querying_events_finished'),
    [HistoryEventsQueryStatus.QUERYING_EVENTS_STARTED]: t('dashboard.history_query_indicator.event_status.querying_events_started'),
    [HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE]: t('dashboard.history_query_indicator.event_status.querying_events_status_update'),
  };

  return statusDescriptions[status] || t('dashboard.history_query_indicator.event_status.default');
}

interface TransactionProgressData {
  currentOperation: string;
  currentOperationData: HistoryQueryProgressOperationData;
}

interface EventProgressData {
  currentOperation: string;
  currentOperationData: HistoryQueryProgressOperationData;
}

/** Cancelled and failed are both terminal: no further progress is coming for that address. */
function isTerminal(status: TxQueryStatusData): boolean {
  return status.status === TransactionsQueryStatus.CANCELLED
    || status.status === TransactionsQueryStatus.FAILED;
}

function isTransactionActive(status: TxQueryStatusData): boolean {
  if (isTerminal(status))
    return false;

  return !isTxQueryStatusFinished(status);
}

function createTransactionProgress(
  activeTxStatus: TxQueryStatusData,
  t: ReturnType<typeof useI18n>['t'],
): TransactionProgressData {
  const statusDesc = getTransactionStatusDescription(activeTxStatus.status, t);

  return {
    currentOperation: statusDesc,
    currentOperationData: {
      address: activeTxStatus.address,
      chain: activeTxStatus.chain,
      status: statusDesc,
      type: 'transaction',
    },
  };
}

function createEventProgress(
  activeEventStatus: HistoryEventsQueryData,
  t: ReturnType<typeof useI18n>['t'],
): EventProgressData {
  const statusDesc = getEventStatusDescription(activeEventStatus.status, t);
  const location = activeEventStatus.location;
  const name = activeEventStatus.name;

  return {
    currentOperation: `${statusDesc} for ${name} (${location})`,
    currentOperationData: {
      location: activeEventStatus.location,
      name: activeEventStatus.name,
      status: statusDesc,
      type: 'event',
    },
  };
}

function isEventFinished(status: HistoryEventsQueryData): boolean {
  return status.status === HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED
    || status.status === HistoryEventsQueryStatus.CANCELLED;
}

export function useHistoryQueryProgress(): UseHistoryQueryProgressReturn {
  const { queryStatus: txQueryStatus } = storeToRefs(useTxQueryStatusStore());
  const { queryStatus: eventsQueryStatus } = storeToRefs(useEventsQueryStatusStore());
  const { t } = useI18n({ useScope: 'global' });
  const rollup = useSyncRollup();

  /**
   * How far the refresh has got, from the ledger rather than from the two websocket stores.
   *
   * @remarks
   * The stores hold only what has been *reported*, so counting them made the denominator grow as
   * addresses and exchanges were discovered — the bar fell whenever new work appeared. The flow
   * declares its whole subtree before any of it runs, so the total is known from the start.
   *
   * Counted in leaves, so this agrees with the sync panel's bar by construction rather than by two
   * implementations happening to round the same way.
   */
  const metrics = computed<{ completedSteps: number; totalItems: number; percentage: number }>(() => ({
    completedSteps: get(rollup.settledLeaves),
    percentage: get(rollup.progress),
    totalItems: get(rollup.declaredLeaves),
  }));

  const progress = computed<HistoryQueryProgress | undefined>(() => {
    const txStatuses = Object.values(get(txQueryStatus));
    const eventStatuses = Object.values(get(eventsQueryStatus));

    if (txStatuses.length === 0 && eventStatuses.length === 0) {
      return undefined;
    }

    const activeTxStatus = txStatuses.find(isTransactionActive);
    if (activeTxStatus) {
      const { currentOperation, currentOperationData } = createTransactionProgress(activeTxStatus, t);
      const { completedSteps, percentage, totalItems } = get(metrics);

      return {
        currentOperation,
        currentOperationData,
        currentStep: completedSteps,
        percentage,
        totalSteps: totalItems,
      };
    }

    const activeEventStatus = eventStatuses.find(status => !isEventFinished(status));

    if (activeEventStatus) {
      const { currentOperation, currentOperationData } = createEventProgress(activeEventStatus, t);
      const { completedSteps, percentage, totalItems } = get(metrics);

      return {
        currentOperation,
        currentOperationData,
        currentStep: completedSteps,
        percentage,
        totalSteps: totalItems,
      };
    }

    const { completedSteps, percentage, totalItems } = get(metrics);
    return {
      currentOperation: null,
      currentOperationData: null,
      currentStep: completedSteps,
      percentage,
      totalSteps: totalItems,
    };
  });

  return {
    progress,
  };
}
