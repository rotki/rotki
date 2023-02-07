import { type ComputedRef, type Ref } from 'vue';
import {
  type EvmTransactionQueryData,
  EvmTransactionsQueryStatus
} from '@/types/websocket-messages';
import { type EvmChainAddress } from '@/types/history/tx/tx';

export const useTxQueryStatusStore = defineStore(
  'history/transaction-query-status',
  () => {
    const queryStatus: Ref<Record<string, EvmTransactionQueryData>> = ref({});

    const setQueryStatus = (data: EvmTransactionQueryData): void => {
      const status = { ...get(queryStatus) };
      const { address, evmChain } = data;
      const key = address + evmChain;

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

    const resetQueryStatus = (): void => {
      set(queryStatus, {});
    };

    const isStatusFinished = (item: EvmTransactionQueryData): boolean => {
      return (
        item.status ===
        EvmTransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED
      );
    };

    const isAllFinished: ComputedRef<boolean> = computed(() => {
      const queryStatusVal = get(queryStatus);
      const addresses = Object.keys(queryStatusVal);

      return addresses.every((address: string) => {
        return isStatusFinished(queryStatusVal[address]);
      });
    });

    const queryingLength: ComputedRef<number> = computed(
      () =>
        Object.values(get(queryStatus)).filter(item => !isStatusFinished(item))
          .length
    );

    const length: ComputedRef<number> = computed(
      () => Object.keys(get(queryStatus)).length
    );

    const removeQueryStatus = (item: EvmChainAddress): void => {
      const statuses = { ...get(queryStatus) };
      set(
        queryStatus,
        Object.fromEntries(
          Object.entries(statuses).filter(
            ([_, status]) =>
              status.evmChain !== item.evmChain ||
              status.address !== item.address
          )
        )
      );
    };

    return {
      queryStatus,
      isAllFinished,
      queryingLength,
      length,
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
