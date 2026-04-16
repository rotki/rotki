import type { ComputedRef, Ref } from 'vue';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useRefWithDebounce } from '@/modules/core/common/use-ref-debounce';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';

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
