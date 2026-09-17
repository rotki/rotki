import type { ComputedRef } from 'vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { type BalanceSource, RefreshSource } from '@/modules/balances/refresh/core/refresh-types';
import { useBalanceRefresh } from '@/modules/balances/use-balance-refresh';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBankData } from '@/modules/banks/use-bank-data';
import { type DashboardRefreshAction, DashboardRefreshKind } from '@/modules/dashboard/dashboard-refresh-action';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseDashboardRefreshReturn {
  /** True while any balance source, token detection or pricing is running. */
  readonly busy: ComputedRef<boolean>;
  /** The sources the user has connected, in menu order; the others have nothing to refresh. */
  readonly sources: ComputedRef<BalanceSource[]>;
  readonly refresh: (action: DashboardRefreshAction) => Promise<void>;
}

export function useDashboardRefresh(): UseDashboardRefreshReturn {
  const { accounts } = storeToRefs(useBlockchainAccountsStore());
  const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
  const { connections } = storeToRefs(useBankConnectionsStore());
  const { useIsActive } = useTaskCenter();
  const { redetectAndRefreshAll, refreshAll, refreshAllPrices, refreshSourceAndPrices } = useBalanceRefresh();
  const { banks } = useBankData();
  const { manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());

  const busy = logicOr(
    useIsActive(ActivityKind.BLOCKCHAIN_BALANCES),
    useIsActive(ActivityKind.EXCHANGE_BALANCES),
    useIsActive(ActivityKind.BANK_BALANCES),
    useIsActive(ActivityKind.MANUAL_BALANCES),
    useIsActive(ActivityKind.TOKEN_DETECTION),
    useIsActive(ActivityKind.PRICES),
  );

  /**
   * Banks count as connected once either their connections or their balances are known, because the
   * connections are only listed lazily and a session can hold bank balances before they are.
   */
  const sources = computed<BalanceSource[]>(() => {
    const connected: BalanceSource[] = [];
    if (Object.values(get(accounts)).some(chainAccounts => chainAccounts.length > 0))
      connected.push(RefreshSource.BLOCKCHAIN);
    if (get(connectedExchanges).length > 0)
      connected.push(RefreshSource.EXCHANGES);
    if (get(connections).length > 0 || get(banks).length > 0)
      connected.push(RefreshSource.BANKS);
    if (get(manualBalances).length > 0 || get(manualLiabilities).length > 0)
      connected.push(RefreshSource.MANUAL);
    return connected;
  });

  async function refresh(action: DashboardRefreshAction): Promise<void> {
    switch (action.kind) {
      case DashboardRefreshKind.BALANCES:
        return refreshAll();
      case DashboardRefreshKind.REDETECT:
        return redetectAndRefreshAll();
      case DashboardRefreshKind.PRICES:
        return refreshAllPrices();
      case DashboardRefreshKind.SOURCE:
        return refreshSourceAndPrices(action.source);
    }
  }

  return {
    busy,
    refresh,
    sources,
  };
}
