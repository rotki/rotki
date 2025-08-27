import type { ComputedRef } from 'vue';
import { get } from '@vueuse/shared';
import { HistoryEventsQueryStatus, TransactionsQueryStatus } from '@/modules/messaging/types';
import { useEventsQueryStatusStore } from '@/store/history/query-status/events-query-status';
import { useTxQueryStatusStore } from '@/store/history/query-status/tx-query-status';
import { truncateAddress } from '@/utils/truncate';

interface HistoryQueryProgress {
  currentStep: number;
  totalSteps: number;
  percentage: number;
  currentOperation: string | null;
  currentOperationData: {
    type: 'transaction' | 'event';
    address?: string;
    chain?: string;
    location?: string;
    name?: string;
    status: string;
  } | null;
}

interface UseHistoryQueryProgressReturn {
  progress: ComputedRef<HistoryQueryProgress | null>;
}

function getTransactionStatusDescription(status: TransactionsQueryStatus, t: ReturnType<typeof useI18n>['t']): string {
  switch (status) {
    case TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED:
      return t('dashboard.history_query_indicator.transaction_status.querying_transactions_started');
    case TransactionsQueryStatus.QUERYING_TRANSACTIONS:
      return t('dashboard.history_query_indicator.transaction_status.querying_transactions');
    case TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED:
      return t('dashboard.history_query_indicator.transaction_status.querying_transactions_finished');
    case TransactionsQueryStatus.QUERYING_INTERNAL_TRANSACTIONS:
      return t('dashboard.history_query_indicator.transaction_status.querying_internal_transactions');
    case TransactionsQueryStatus.QUERYING_EVM_TOKENS_TRANSACTIONS:
      return t('dashboard.history_query_indicator.transaction_status.querying_evm_tokens_transactions');
    case TransactionsQueryStatus.DECODING_TRANSACTIONS_STARTED:
      return t('dashboard.history_query_indicator.transaction_status.decoding_transactions_started');
    case TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED:
      return t('dashboard.history_query_indicator.transaction_status.decoding_transactions_finished');
    case TransactionsQueryStatus.ACCOUNT_CHANGE:
      return t('dashboard.history_query_indicator.transaction_status.querying_transactions_started');
    default:
      return t('dashboard.history_query_indicator.transaction_status.default');
  }
}

function getEventStatusDescription(status: HistoryEventsQueryStatus, t: ReturnType<typeof useI18n>['t']): string {
  switch (status) {
    case HistoryEventsQueryStatus.QUERYING_EVENTS_STARTED:
      return t('dashboard.history_query_indicator.event_status.querying_events_started');
    case HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE:
      return t('dashboard.history_query_indicator.event_status.querying_events_status_update');
    case HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED:
      return t('dashboard.history_query_indicator.event_status.querying_events_finished');
    default:
      return t('dashboard.history_query_indicator.event_status.default');
  }
}

export function useHistoryQueryProgress(): UseHistoryQueryProgressReturn {
  const { queryStatus: txQueryStatus } = storeToRefs(useTxQueryStatusStore());
  const { queryStatus: eventsQueryStatus } = storeToRefs(useEventsQueryStatusStore());
  const { t } = useI18n({ useScope: 'global' });

  const progress = computed<HistoryQueryProgress | null>(() => {
    const txStatuses = Object.values(get(txQueryStatus));
    const eventStatuses = Object.values(get(eventsQueryStatus));

    const totalItems = txStatuses.length + eventStatuses.length;

    if (totalItems === 0) {
      return null;
    }

    // Find current operation (first non-finished item)
    let currentOperation: string | null = null;
    let currentOperationData: HistoryQueryProgress['currentOperationData'] = null;

    // Check transaction statuses for current operation
    const activeTxStatus = txStatuses.find((status) => {
      if (status.subtype === 'bitcoin') {
        return status.status !== TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED;
      }
      return status.status !== TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED;
    });

    if (activeTxStatus) {
      const statusDesc = getTransactionStatusDescription(activeTxStatus.status, t);
      const address = truncateAddress(activeTxStatus.address, 6);
      const chain = activeTxStatus.chain.toUpperCase();
      currentOperation = `${statusDesc} for ${address} on ${chain}`;
      currentOperationData = {
        address: activeTxStatus.address,
        chain: activeTxStatus.chain,
        status: statusDesc,
        type: 'transaction',
      };
    }

    // If no active tx, check event statuses
    if (!currentOperation) {
      const activeEventStatus = eventStatuses.find(
        status => status.status !== HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED,
      );

      if (activeEventStatus) {
        const statusDesc = getEventStatusDescription(activeEventStatus.status, t);
        const location = activeEventStatus.location;
        const name = activeEventStatus.name;
        currentOperation = `${statusDesc} for ${name} (${location})`;
        currentOperationData = {
          location: activeEventStatus.location,
          name: activeEventStatus.name,
          status: statusDesc,
          type: 'event',
        };
      }
    }

    // Count finished items
    const finishedTxItems = txStatuses.filter((status) => {
      if (status.subtype === 'bitcoin') {
        return status.status === TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED;
      }
      return status.status === TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED;
    }).length;

    const finishedEventItems = eventStatuses.filter(
      status => status.status === HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED,
    ).length;

    const completedSteps = finishedTxItems + finishedEventItems;
    const percentage = totalItems > 0 ? Math.round((completedSteps / totalItems) * 100) : 0;

    return {
      currentOperation,
      currentOperationData,
      currentStep: completedSteps,
      percentage,
      totalSteps: totalItems,
    };
  });

  return {
    progress,
  };
}
