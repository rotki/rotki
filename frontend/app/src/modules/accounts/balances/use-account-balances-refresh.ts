import type { MaybeRef } from '@vueuse/core';
import type { Ref } from 'vue';
import { useAccountCategoryHelper } from '@/composables/accounts/use-account-category-helper';
import { useRefresh } from '@/composables/balances/refresh';
import { useBlockchains } from '@/composables/blockchain';

interface AccountBalancesRefreshOptions {
  category: MaybeRef<string>;
  fetchData: () => Promise<void>;
  detailsTable: Ref<{ refresh: () => Promise<void> } | undefined>;
}

interface AccountBalancesRefreshReturn {
  refresh: () => Promise<void>;
  refreshClick: () => Promise<void>;
}

export function useAccountBalancesRefresh(options: AccountBalancesRefreshOptions): AccountBalancesRefreshReturn {
  const { category, detailsTable, fetchData } = options;

  const { handleBlockchainRefresh, refreshBlockchainBalances } = useRefresh();
  const { fetchAccounts } = useBlockchains();
  const { chainIds, isEvm } = useAccountCategoryHelper(category);

  const refreshClick = async (): Promise<void> => {
    await fetchAccounts(get(chainIds), true);
    if (get(isEvm))
      await handleBlockchainRefresh();
    else
      await refreshBlockchainBalances(get(chainIds));
    await fetchData();
  };

  const refresh = async (): Promise<void> => {
    await fetchData();
    if (!isDefined(detailsTable))
      return;

    await get(detailsTable).refresh();
  };

  return {
    refresh,
    refreshClick,
  };
}
