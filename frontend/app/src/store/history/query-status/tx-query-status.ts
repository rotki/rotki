import {
  type EvmTransactionQueryData,
  EvmTransactionsQueryStatus
} from '@/types/websocket-messages';

export const useTxQueryStatusStore = defineStore(
  'history/transaction-query-status',
  () => {
    const createKey = ({
      address,
      evmChain
    }: {
      address: string;
      evmChain: string;
    }) => address + evmChain;

    const setQueryStatus = (data: EvmTransactionQueryData): void => {
      const status = { ...get(queryStatus) };
      const key = createKey(data);

      if (data.status === EvmTransactionsQueryStatus.ACCOUNT_CHANGE) {
        return;
      }

      if (
        data.status === EvmTransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED
      ) {
        status[key] = {
          ...data,
          status: EvmTransactionsQueryStatus.QUERYING_TRANSACTIONS
        };
      } else {
        status[key] = data;
      }

      set(queryStatus, status);
    };

    const isStatusFinished = (item: EvmTransactionQueryData): boolean =>
      item.status === EvmTransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED;

    const {
      queryStatus,
      isAllFinished,
      removeQueryStatus: remove,
      resetQueryStatus
    } = useQueryStatusStore<EvmTransactionQueryData>(
      isStatusFinished,
      createKey
    );

    const removeQueryStatus = (data: { address: string; evmChain: string }) => {
      remove(createKey(data));
    };

    return {
      queryStatus,
      isAllFinished,
      isStatusFinished,
      setQueryStatus,
      removeQueryStatus,
      resetQueryStatus
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useTxQueryStatusStore, import.meta.hot)
  );
}
