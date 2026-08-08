import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useBalancesLoading } from '@/modules/balances/use-balance-loading';
import { useRefWithDebounce } from '@/modules/core/common/use-ref-debounce';

interface UseBalanceQueriesReturn {
  useQueryingBalances: ComputedRef<boolean>;
  warnUntrackedAddress: ComputedRef<boolean>;
}

export function useBalanceQueries(connected: MaybeRefOrGetter<boolean>, connectedAddress: MaybeRefOrGetter<string | undefined>): UseBalanceQueriesReturn {
  const { loadingBlockchainBalances: queryingBalances } = useBalancesLoading();
  const { addresses } = useAccountAddresses();

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
