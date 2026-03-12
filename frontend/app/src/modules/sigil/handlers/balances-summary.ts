import type { BalancesSummaryPayload } from '@/modules/sigil/types';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';

export function useBalancesSummaryHandler(): () => BalancesSummaryPayload {
  const { accounts } = storeToRefs(useBlockchainAccountsStore());
  const { manualBalances } = storeToRefs(useBalancesStore());
  const { assets } = useAggregatedBalances();

  return () => {
    const chainAccounts = get(accounts);
    const dynamicKeys: Record<string, number> = {};
    let totalAccounts = 0;

    for (const chain in chainAccounts) {
      const count = chainAccounts[chain].length;
      if (count === 0)
        continue;
      dynamicKeys[`accounts_${chain}`] = count;
      totalAccounts += count;
    }

    return {
      ...dynamicKeys,
      hasManualBalances: get(manualBalances).length > 0,
      distinctAssetCount: get(assets).length,
      totalAccounts,
      totalChains: Object.keys(dynamicKeys).length,
    };
  };
}
