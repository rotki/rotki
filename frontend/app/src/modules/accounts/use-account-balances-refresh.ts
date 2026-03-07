import type { MaybeRefOrGetter } from 'vue';
import { useBlockchainAccountManagement } from '@/modules/accounts/use-blockchain-account-management';
import { useBalanceRefresh } from '@/modules/balances/use-balance-refresh';

interface UseAccountBalancesRefreshOptions {
  /** The blockchain chain IDs to refresh balances for. */
  chainIds: MaybeRefOrGetter<string[]>;
  /** Whether the selected chains are EVM-compatible. */
  isEvm: MaybeRefOrGetter<boolean>;
  /** Callback to fetch additional data after balance refresh. */
  fetchData: () => Promise<void>;
}

interface UseAccountBalancesRefreshReturn {
  refreshClick: () => Promise<void>;
}

export function useAccountBalancesRefresh(
  options: UseAccountBalancesRefreshOptions,
): UseAccountBalancesRefreshReturn {
  const { chainIds, fetchData, isEvm } = options;

  const { handleBlockchainRefresh, refreshBlockchainBalances } = useBalanceRefresh();
  const { fetchAccounts } = useBlockchainAccountManagement();

  async function refreshClick(): Promise<void> {
    const chains = toValue(chainIds);
    await fetchAccounts(chains, true);
    if (toValue(isEvm))
      await handleBlockchainRefresh(chains);
    else
      await refreshBlockchainBalances(chains);

    await fetchData();
  }

  return {
    refreshClick,
  };
}
