import type { Blockchain } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef, Ref } from 'vue';
import { useQueryStatus } from '@/composables/history/events/query-status/index';
import { useSupportedChains } from '@/composables/info/chains';
import { useTxQueryStatusStore } from '@/store/history/query-status/tx-query-status';
import { type EvmTransactionQueryData, EvmTransactionsQueryStatus } from '@/types/websocket-messages';

type TranslationKey = 'transactions.query_status.done_date_range'
  | 'transactions.query_status.done_end_date'
  | 'transactions.query_status.date_range'
  | 'transactions.query_status.end_date';

interface Status { index: number; label?: string }

type Statuses = Record<EvmTransactionsQueryStatus, Status>;

interface UseTransactionQueryStatusReturn {
  getLabel: (data: EvmTransactionQueryData) => string;
  getStatusData: (data: EvmTransactionQueryData) => Status;
  getItemTranslationKey: (item: EvmTransactionQueryData) => TranslationKey;
  isQueryFinished: (item: EvmTransactionQueryData) => boolean;
  getKey: (item: EvmTransactionQueryData) => string;
  resetQueryStatus: () => void;
  isAllFinished: ComputedRef<boolean>;
  sortedQueryStatus: Ref<EvmTransactionQueryData[]>;
  filtered: ComputedRef<EvmTransactionQueryData[]>;
  queryingLength: ComputedRef<number>;
  length: ComputedRef<number>;
}

export function useTransactionQueryStatus(onlyChains: MaybeRef<Blockchain[]> = []): UseTransactionQueryStatusReturn {
  const { t } = useI18n({ useScope: 'global' });
  const store = useTxQueryStatusStore();
  const { isStatusFinished, resetQueryStatus } = store;
  const { isAllFinished, queryStatus } = storeToRefs(store);
  const { getChain } = useSupportedChains();

  const filtered = computed<EvmTransactionQueryData[]>(() => {
    const statuses = Object.values(get(queryStatus));
    const chains = get(onlyChains);
    if (chains.length === 0)
      return statuses;

    return statuses.filter(({ evmChain }) => chains.includes(getChain(evmChain)));
  });

  const { isQueryStatusRange, length, queryingLength, sortedQueryStatus } = useQueryStatus(filtered, isStatusFinished);

  const statusesData = computed<Statuses>(() => ({
    [EvmTransactionsQueryStatus.ACCOUNT_CHANGE]: {
      index: 0,
      label: t('transactions.query_status.statuses.pending'),
    },
    [EvmTransactionsQueryStatus.QUERYING_EVM_TOKENS_TRANSACTIONS]: {
      index: 3,
      label: t('transactions.query_status.statuses.querying_evm_tokens_transactions'),
    },
    [EvmTransactionsQueryStatus.QUERYING_INTERNAL_TRANSACTIONS]: {
      index: 2,
      label: t('transactions.query_status.statuses.querying_internal_transactions'),
    },
    [EvmTransactionsQueryStatus.QUERYING_TRANSACTIONS]: {
      index: 1,
      label: t('transactions.query_status.statuses.querying_transactions'),
    },
    [EvmTransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED]: {
      index: 4,
    },
    [EvmTransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED]: {
      index: -1,
    },
  }));

  const getStatusData = (data: EvmTransactionQueryData): Status => get(statusesData)[data.status];

  const getLabel = (data: EvmTransactionQueryData): string => getStatusData(data)?.label ?? '';

  const getItemTranslationKey = (item: EvmTransactionQueryData): TranslationKey => {
    const isRange = isQueryStatusRange(item);

    if (isStatusFinished(item))
      return isRange ? 'transactions.query_status.done_date_range' : 'transactions.query_status.done_end_date';

    return isRange ? 'transactions.query_status.date_range' : 'transactions.query_status.end_date';
  };

  const getKey = (item: EvmTransactionQueryData): string => item.address + item.evmChain;

  const isQueryFinished = (item: EvmTransactionQueryData): boolean => isStatusFinished(item);

  return {
    filtered,
    getItemTranslationKey,
    getKey,
    getLabel,
    getStatusData,
    isAllFinished,
    isQueryFinished,
    length,
    queryingLength,
    resetQueryStatus,
    sortedQueryStatus,
  };
}
