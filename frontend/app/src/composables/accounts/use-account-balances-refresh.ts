import type { Ref } from 'vue';
import { useRefresh } from '@/composables/balances/refresh';
import { useBlockchains } from '@/composables/blockchain';

interface UseAccountBalancesRefreshOptions {
  chainIds: Ref<string[]>;
  isEvm: Ref<boolean>;
  fetchData: () => Promise<void>;
}

interface UseAccountBalancesRefreshReturn {
  refreshClick: () => Promise<void>;
}

export function useAccountBalancesRefresh(
  options: UseAccountBalancesRefreshOptions,
): UseAccountBalancesRefreshReturn {
  const { chainIds, fetchData, isEvm } = options;

  const { handleBlockchainRefresh, refreshBlockchainBalances } = useRefresh();
  const { fetchAccounts } = useBlockchains();

  async function refreshClick(): Promise<void> {
    const chains = get(chainIds);
    await fetchAccounts(chains, true);
    if (get(isEvm))
      await handleBlockchainRefresh(chains);
    else
      await refreshBlockchainBalances(chains);

    await fetchData();
  }

  return {
    refreshClick,
  };
}
