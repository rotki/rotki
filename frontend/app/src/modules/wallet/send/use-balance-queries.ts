import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useRefWithDebounce } from '@/modules/core/common/use-ref-debounce';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseBalanceQueriesReturn {
  useQueryingBalances: ComputedRef<boolean>;
  warnUntrackedAddress: ComputedRef<boolean>;
}

export function useBalanceQueries(connected: MaybeRefOrGetter<boolean>, connectedAddress: MaybeRefOrGetter<string | undefined>): UseBalanceQueriesReturn {
  const { useIsActive } = useTaskCenter();
  const { addresses } = useAccountAddresses();

  const queryingBalances = useIsActive(ActivityKind.BLOCKCHAIN_BALANCES);
  const useQueryingBalances = useRefWithDebounce(queryingBalances, 200);

  const warnUntrackedAddress = computed<boolean>(() => {
    const address = toValue(connectedAddress);
    const connectedVal = toValue(connected);

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
