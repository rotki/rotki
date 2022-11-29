import { type ComputedRef } from 'vue';
import {
  type EthereumTransactionQueryData,
  EthereumTransactionsQueryStatus
} from '@/types/websocket-messages';

export const useTxQueryStatus = defineStore(
  'history/transactionsQueryStatus',
  () => {
    const queryStatus = ref<Record<string, EthereumTransactionQueryData>>({});

    const setQueryStatus = (data: EthereumTransactionQueryData): void => {
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

    const resetQueryStatus = (): void => {
      set(queryStatus, {});
    };

    const isStatusFinished = (item: EthereumTransactionQueryData) => {
      return (
        item.status ===
        EthereumTransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED
      );
    };

    const isAllFinished: ComputedRef<boolean> = computed(() => {
      const queryStatusVal = get(queryStatus);
      const addresses = Object.keys(queryStatusVal);

      return addresses.every((address: string) => {
        return isStatusFinished(queryStatusVal[address]);
      });
    });

    return {
      queryStatus,
      isAllFinished,
      isStatusFinished,
      setQueryStatus,
      resetQueryStatus
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useTxQueryStatus, import.meta.hot));
}
