import { type Blockchain } from '@rotki/common/lib/blockchain';
import { type MaybeRef } from '@vueuse/core';
import {
  type EvmTransactionQueryData,
  EvmTransactionsQueryStatus
} from '@/types/websocket-messages';

export const useTransactionQueryStatus = (
  onlyChains: MaybeRef<Blockchain[]> = []
) => {
  const { t } = useI18n();
  const store = useTxQueryStatusStore();
  const { isStatusFinished, resetQueryStatus } = store;
  const { queryStatus, isAllFinished } = storeToRefs(store);
  const { getChain } = useSupportedChains();

  const filtered: ComputedRef<EvmTransactionQueryData[]> = computed(() => {
    const statuses = Object.values(get(queryStatus));
    const chains = get(onlyChains);
    if (chains.length === 0) {
      return statuses;
    }

    return statuses.filter(({ evmChain }) =>
      chains.includes(getChain(evmChain))
    );
  });

  const statusesData = computed(() => ({
    [EvmTransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED]: {
      index: -1
    },
    [EvmTransactionsQueryStatus.ACCOUNT_CHANGE]: {
      index: 0
    },
    [EvmTransactionsQueryStatus.QUERYING_TRANSACTIONS]: {
      index: 1,
      label: t('transactions.query_status.statuses.querying_transactions')
    },
    [EvmTransactionsQueryStatus.QUERYING_INTERNAL_TRANSACTIONS]: {
      index: 2,
      label: t(
        'transactions.query_status.statuses.querying_internal_transactions'
      )
    },
    [EvmTransactionsQueryStatus.QUERYING_EVM_TOKENS_TRANSACTIONS]: {
      index: 3,
      label: t(
        'transactions.query_status.statuses.querying_evm_tokens_transactions'
      )
    },
    [EvmTransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED]: {
      index: 4
    }
  }));

  const getStatusData = (data: EvmTransactionQueryData) =>
    get(statusesData)[data.status];

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

  const { sortedQueryStatus, queryingLength, length, isQueryStatusRange } =
    useQueryStatus(filtered, isStatusFinished);

  const getKey = (item: EvmTransactionQueryData) =>
    item.address + item.evmChain;

  const isQueryFinished = (item: EvmTransactionQueryData) =>
    isStatusFinished(item);

  return {
    getLabel,
    getStatusData,
    getItemTranslationKey,
    isQueryFinished,
    getKey,
    resetQueryStatus,
    isAllFinished,
    sortedQueryStatus,
    filtered,
    queryingLength,
    length
  };
};
