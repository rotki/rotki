import {
  type EvmTransactionQueryData,
  EvmTransactionsQueryStatus
} from '@/types/websocket-messages';
import { useTxQueryStatusStore } from '@/store/history/query-status';

export const useTransactionQueryStatus = () => {
  const { tc } = useI18n();
  const { isStatusFinished } = useTxQueryStatusStore();

  const statusesData = computed(() => ({
    [EvmTransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED]: {
      index: -1
    },
    [EvmTransactionsQueryStatus.ACCOUNT_CHANGE]: {
      index: 0
    },
    [EvmTransactionsQueryStatus.QUERYING_TRANSACTIONS]: {
      index: 1,
      label: tc('transactions.query_status.statuses.querying_transactions')
    },
    [EvmTransactionsQueryStatus.QUERYING_INTERNAL_TRANSACTIONS]: {
      index: 2,
      label: tc(
        'transactions.query_status.statuses.querying_internal_transactions'
      )
    },
    [EvmTransactionsQueryStatus.QUERYING_EVM_TOKENS_TRANSACTIONS]: {
      index: 3,
      label: tc(
        'transactions.query_status.statuses.querying_evm_tokens_transactions'
      )
    },
    [EvmTransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED]: {
      index: 4
    }
  }));

  const isQueryStatusRange = (data: EvmTransactionQueryData) => {
    return data.period?.[0] > 0;
  };

  const getStatusData = (data: EvmTransactionQueryData) => {
    return get(statusesData)[data.status];
  };

  const getLabel = (data: EvmTransactionQueryData) => {
    const statusData = getStatusData(data);
    if ('label' in statusData) {
      return statusData.label;
    }

    return '';
  };

  const getItemTranslationKey = (item: EvmTransactionQueryData) => {
    const isRange = isQueryStatusRange(item);

    if (isStatusFinished(item)) {
      return isRange
        ? 'transactions.query_status.done_date_range'
        : 'transactions.query_status.done_end_date';
    }

    return isRange
      ? 'transactions.query_status.date_range'
      : 'transactions.query_status.end_date';
  };

  return {
    getLabel,
    getStatusData,
    getItemTranslationKey,
    isStatusFinished
  };
};
