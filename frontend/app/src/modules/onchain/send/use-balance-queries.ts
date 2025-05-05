import type { ComputedRef, Ref } from 'vue';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

interface UseBalanceQueriesReturn {
  addressTracked: ComputedRef<boolean>;
  useQueryingBalances: ComputedRef<boolean>;
}

export function useBalanceQueries(connected: Ref<boolean>, connectedAddress: Ref<string | undefined>): UseBalanceQueriesReturn {
  const { useIsTaskRunning } = useTaskStore();
  const { addresses } = useAccountAddresses();

  const queryingBalances = useIsTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);
  const queryingBalancesDebounced = refDebounced(queryingBalances, 200);
  const useQueryingBalances = logicOr(queryingBalances, queryingBalancesDebounced);

  const addressTracked = computed<boolean>(() => {
    const connectedVal = get(connected);
    const address = get(connectedAddress);

    if (!connectedVal || !address) {
      return false;
    }

    const accountsAddresses = [...new Set(Object.values(get(addresses)).flat())];
    return connectedVal && accountsAddresses.includes(address);
  });

  return {
    addressTracked,
    useQueryingBalances,
  };
}
