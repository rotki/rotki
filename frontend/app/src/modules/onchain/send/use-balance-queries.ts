import type { ComputedRef, Ref } from 'vue';
import { useRefWithDebounce } from '@/composables/ref';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

interface UseBalanceQueriesReturn {
  useQueryingBalances: ComputedRef<boolean>;
  warnUntrackedAddress: ComputedRef<boolean>;
}

export function useBalanceQueries(connected: Ref<boolean>, connectedAddress: Ref<string | undefined>): UseBalanceQueriesReturn {
  const { useIsTaskRunning } = useTaskStore();
  const { addresses } = useAccountAddresses();

  const queryingBalances = useIsTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);
  const useQueryingBalances = useRefWithDebounce(queryingBalances, 200);

  const warnUntrackedAddress = computed<boolean>(() => {
    const address = get(connectedAddress);
    const connectedVal = get(connected);

    // Only warn if connected, has an address, and address is not tracked
    if (!connectedVal || !address || address.length === 0) {
      return false;
    }

    const accountsAddresses = [...new Set(Object.values(get(addresses)).flat())];
    return !accountsAddresses.includes(address);
  });

  return {
    useQueryingBalances,
    warnUntrackedAddress,
  };
}
