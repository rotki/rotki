import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef, Ref } from 'vue';
import { useRefMap } from '@/composables/utils/useRefMap';
import { TransactionsQueryStatus } from '@/modules/messaging/types';
import { isBitcoinTxQueryStatusData, type TxQueryStatusData, useTxQueryStatusStore } from '@/store/history/query-status/tx-query-status';

type TranslationKey = 'transactions.query_status.done_date_range'
  | 'transactions.query_status.done_end_date'
  | 'transactions.query_status.date_range'
  | 'transactions.query_status.end_date'
  | 'transactions.query_status.start_decoding'
  | 'transactions.query_status.start_querying'
  | 'transactions.query_status.done_querying';

interface Status { index: number; label?: string }

type Statuses = Record<TransactionsQueryStatus, Status>;

interface UseTransactionQueryStatusReturn {
  getLabel: (data: TxQueryStatusData) => string;
  getStatusData: (data: TxQueryStatusData) => Status;
  getItemTranslationKey: (item: TxQueryStatusData) => TranslationKey;
  isQueryFinished: (item: TxQueryStatusData) => boolean;
  getKey: (item: TxQueryStatusData) => string;
  resetQueryStatus: () => void;
  isAllFinished: ComputedRef<boolean>;
  sortedQueryStatus: Ref<TxQueryStatusData[]>;
  filtered: ComputedRef<TxQueryStatusData[]>;
  queryingLength: ComputedRef<number>;
  length: ComputedRef<number>;
}

export function useTransactionQueryStatus(onlyChains: MaybeRef<string[]> = []): UseTransactionQueryStatusReturn {
  const { t } = useI18n({ useScope: 'global' });
  const store = useTxQueryStatusStore();
  const { isStatusFinished, resetQueryStatus } = store;
  const { isAllFinished, queryStatus } = storeToRefs(store);

  const filtered = computed<TxQueryStatusData[]>(() => {
    const statuses = Object.values(get(queryStatus));
    const chains = get(onlyChains);
    if (chains.length === 0)
      return statuses;

    return statuses.filter(({ chain }) => chains.includes(chain));
  });

  const sortedQueryStatus = useSorted<TxQueryStatusData>(filtered, (a, b) => (isStatusFinished(a) ? 1 : 0) - (isStatusFinished(b) ? 1 : 0));

  const queryingLength = computed<number>(
    () => get(filtered).filter(item => !isStatusFinished(item)).length,
  );

  const length = useRefMap(filtered, (arr: TxQueryStatusData[]) => arr.length);

  const isQueryStatusRange = (data: TxQueryStatusData): boolean => {
    if (!isBitcoinTxQueryStatusData(data) && data.period)
      return data.period[0] > 0;

    return false;
  };

  const statusesData = computed<Statuses>(() => ({
    [TransactionsQueryStatus.ACCOUNT_CHANGE]: {
      index: 0,
      label: t('transactions.query_status.statuses.pending'),
    },
    [TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED]: {
      index: 6,
    },
    [TransactionsQueryStatus.DECODING_TRANSACTIONS_STARTED]: {
      index: 5,
    },
    [TransactionsQueryStatus.QUERYING_EVM_TOKENS_TRANSACTIONS]: {
      index: 3,
      label: t('transactions.query_status.statuses.querying_evm_tokens_transactions'),
    },
    [TransactionsQueryStatus.QUERYING_INTERNAL_TRANSACTIONS]: {
      index: 2,
      label: t('transactions.query_status.statuses.querying_internal_transactions'),
    },
    [TransactionsQueryStatus.QUERYING_TRANSACTIONS]: {
      index: 1,
      label: t('transactions.query_status.statuses.querying_transactions'),
    },
    [TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED]: {
      index: 4,
      label: t('transactions.query_status.statuses.querying_finished'),
    },
    [TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED]: {
      index: -1,
      label: t('transactions.query_status.statuses.querying_started'),
    },
  }));

  const getStatusData = (data: TxQueryStatusData): Status => get(statusesData)[data.status];

  const getLabel = (data: TxQueryStatusData): string => getStatusData(data)?.label ?? '';

  const getItemTranslationKey = (item: TxQueryStatusData): TranslationKey => {
    const isRange = isQueryStatusRange(item);

    if (isBitcoinTxQueryStatusData(item)) {
      if (item.status === TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED) {
        return 'transactions.query_status.start_querying';
      }
      else if (item.status === TransactionsQueryStatus.DECODING_TRANSACTIONS_STARTED) {
        return 'transactions.query_status.start_decoding';
      }
      else {
        return 'transactions.query_status.done_querying';
      }
    }

    if (isStatusFinished(item))
      return isRange ? 'transactions.query_status.done_date_range' : 'transactions.query_status.done_end_date';

    return isRange ? 'transactions.query_status.date_range' : 'transactions.query_status.end_date';
  };

  const getKey = (item: TxQueryStatusData): string => item.address + item.chain;

  const isQueryFinished = (item: TxQueryStatusData): boolean => isStatusFinished(item);

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
