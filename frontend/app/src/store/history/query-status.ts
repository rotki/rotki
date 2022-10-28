import {
  EthereumTransactionQueryData,
  EthereumTransactionsQueryStatus
} from '@/types/websocket-messages';

export const useTxQueryStatus = defineStore(
  'history/transactionsQueryStatus',
  () => {
    const queryStatus = ref<{
      [address: string]: EthereumTransactionQueryData;
    }>({});

    const setQueryStatus = (data: EthereumTransactionQueryData) => {
      const status = { ...get(queryStatus) };
      const address = data.address;

      if (data.status === EthereumTransactionsQueryStatus.ACCOUNT_CHANGE) {
        return;
      }

      if (
        data.status ===
        EthereumTransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED
      ) {
        status[address] = {
          ...data,
          status: EthereumTransactionsQueryStatus.QUERYING_TRANSACTIONS
        };
      } else {
        status[address] = data;
      }

      set(queryStatus, status);
    };

    const resetQueryStatus = () => {
      set(queryStatus, {});
    };

    const reset = () => {
      resetQueryStatus();
    };

    return {
      queryStatus,
      setQueryStatus,
      resetQueryStatus,
      reset
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useTxQueryStatus, import.meta.hot));
}
