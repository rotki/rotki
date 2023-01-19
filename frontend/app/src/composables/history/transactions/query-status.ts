import {
  type EthereumTransactionQueryData,
  EthereumTransactionsQueryStatus
} from '@/types/websocket-messages';
import { useTxQueryStatusStore } from '@/store/history/query-status';

export const useTransactionQueryStatus = () => {
  const { tc } = useI18n();
  const { isStatusFinished } = useTxQueryStatusStore();

  const statusesData = computed(() => ({
    [EthereumTransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED]: {
      index: -1
    },
    [EthereumTransactionsQueryStatus.ACCOUNT_CHANGE]: {
      index: 0
    },
    [EthereumTransactionsQueryStatus.QUERYING_TRANSACTIONS]: {
      index: 1,
      label: tc('transactions.query_status.statuses.querying_transactions')
    },
    [EthereumTransactionsQueryStatus.QUERYING_INTERNAL_TRANSACTIONS]: {
      index: 2,
      label: tc(
        'transactions.query_status.statuses.querying_internal_transactions'
      )
    },
    [EthereumTransactionsQueryStatus.QUERYING_EVM_TOKENS_TRANSACTIONS]: {
      index: 3,
      label: tc(
        'transactions.query_status.statuses.querying_evm_tokens_transactions'
      )
    },
    [EthereumTransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED]: {
      index: 4
    }
  }));

  const isQueryStatusRange = (data: EthereumTransactionQueryData) => {
    return data.period?.[0] > 0;
  };

  const getStatusData = (data: EthereumTransactionQueryData) => {
    return get(statusesData)[data.status];
  };

  const getLabel = (data: EthereumTransactionQueryData) => {
    const statusData = getStatusData(data);
    if ('label' in statusData) {
      return statusData.label;
    }

    return '';
  };

  const getItemTranslationKey = (item: EthereumTransactionQueryData) => {
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
