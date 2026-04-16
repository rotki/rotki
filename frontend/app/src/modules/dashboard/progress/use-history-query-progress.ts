import type { ComputedRef } from 'vue';
import type { CommonQueryProgressData, HistoryQueryProgressType } from '@/modules/dashboard/progress/types';
import { get } from '@vueuse/shared';
import {
  type HistoryEventsQueryData,
  HistoryEventsQueryStatus,
  TransactionsQueryStatus,
} from '@/modules/core/messaging/types';
import { useEventsQueryStatusStore } from '@/modules/history/use-events-query-status-store';
import { type TxQueryStatusData, useTxQueryStatusStore } from '@/modules/history/use-tx-query-status-store';

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

function isTransactionActive(status: TxQueryStatusData): boolean {
  if (status.status === TransactionsQueryStatus.CANCELLED)
    return false;

  if (status.subtype === 'bitcoin') {
    return status.status !== TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED;
  }
  return status.status !== TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED;
}

function isTransactionFinished(status: TxQueryStatusData): boolean {
  if (status.status === TransactionsQueryStatus.CANCELLED)
    return true;

  if (status.subtype === 'bitcoin') {
    return status.status === TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED;
  }
  return status.status === TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED;
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

function calculateProgressMetrics(
  txStatuses: TxQueryStatusData[],
  eventStatuses: HistoryEventsQueryData[],
): { completedSteps: number; totalItems: number; percentage: number } {
  const finishedTxItems = txStatuses.filter(isTransactionFinished).length;
  const finishedEventItems = eventStatuses.filter(isEventFinished).length;

  const completedSteps = finishedTxItems + finishedEventItems;
  const totalItems = txStatuses.length + eventStatuses.length;
  const percentage = totalItems > 0 ? Math.round((completedSteps / totalItems) * 100) : 0;

  return { completedSteps, percentage, totalItems };
}

export function useHistoryQueryProgress(): UseHistoryQueryProgressReturn {
  const { queryStatus: txQueryStatus } = storeToRefs(useTxQueryStatusStore());
  const { queryStatus: eventsQueryStatus } = storeToRefs(useEventsQueryStatusStore());
  const { t } = useI18n({ useScope: 'global' });

  const progress = computed<HistoryQueryProgress | undefined>(() => {
    const txStatuses = Object.values(get(txQueryStatus));
    const eventStatuses = Object.values(get(eventsQueryStatus));

    if (txStatuses.length === 0 && eventStatuses.length === 0) {
      return undefined;
    }

    // Check for active transaction
    const activeTxStatus = txStatuses.find(isTransactionActive);
    if (activeTxStatus) {
      const { currentOperation, currentOperationData } = createTransactionProgress(activeTxStatus, t);
      const metrics = calculateProgressMetrics(txStatuses, eventStatuses);

      return {
        currentOperation,
        currentOperationData,
        currentStep: metrics.completedSteps,
        percentage: metrics.percentage,
        totalSteps: metrics.totalItems,
      };
    }

    // Check for active event
    const activeEventStatus = eventStatuses.find(status => !isEventFinished(status));

    if (activeEventStatus) {
      const { currentOperation, currentOperationData } = createEventProgress(activeEventStatus, t);
      const metrics = calculateProgressMetrics(txStatuses, eventStatuses);

      return {
        currentOperation,
        currentOperationData,
        currentStep: metrics.completedSteps,
        percentage: metrics.percentage,
        totalSteps: metrics.totalItems,
      };
    }

    // No active operations
    const metrics = calculateProgressMetrics(txStatuses, eventStatuses);
    return {
      currentOperation: null,
      currentOperationData: null,
      currentStep: metrics.completedSteps,
      percentage: metrics.percentage,
      totalSteps: metrics.totalItems,
    };
  });

  return {
    progress,
  };
}
