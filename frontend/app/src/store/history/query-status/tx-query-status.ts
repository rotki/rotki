import type { EvmChainAddress } from '@/types/history/events/index';
import { useQueryStatusStore } from '@/store/history/query-status/index';
import { type EvmTransactionQueryData, EvmTransactionsQueryStatus } from '@/types/websocket-messages';

export const useTxQueryStatusStore = defineStore('history/transaction-query-status', () => {
  const createKey = ({ address, evmChain }: EvmChainAddress): string => address + evmChain;

  const isStatusFinished = (item: EvmTransactionQueryData): boolean =>
    item.status === EvmTransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED;

  const {
    isAllFinished,
    queryStatus,
    removeQueryStatus: remove,
    resetQueryStatus,
  } = useQueryStatusStore<EvmTransactionQueryData>(isStatusFinished, createKey);

  const setQueryStatus = (data: EvmTransactionQueryData): void => {
    const status = { ...get(queryStatus) };
    const key = createKey(data);

    if (data.status === EvmTransactionsQueryStatus.ACCOUNT_CHANGE)
      return;

    if (data.status === EvmTransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED) {
      status[key] = {
        ...data,
        status: EvmTransactionsQueryStatus.QUERYING_TRANSACTIONS,
      };
    }
    else {
      status[key] = data;
    }

    set(queryStatus, status);
  };

  const initializeQueryStatus = (data: EvmChainAddress[]): void => {
    resetQueryStatus();

    const status = { ...get(queryStatus) };
    const now = Date.now() / 1000;
    for (const item of data) {
      const key = createKey(item);
      status[key] = {
        ...item,
        period: [0, now],
        status: EvmTransactionsQueryStatus.ACCOUNT_CHANGE,
      };
    }
    set(queryStatus, status);
  };

  const removeQueryStatus = (data: EvmChainAddress): void => {
    remove(createKey(data));
  };

  return {
    initializeQueryStatus,
    isAllFinished,
    isStatusFinished,
    queryStatus,
    removeQueryStatus,
    resetQueryStatus,
    setQueryStatus,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useTxQueryStatusStore, import.meta.hot));
