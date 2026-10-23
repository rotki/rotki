import type { ComputedRef } from 'vue';
import type { WorkStatus } from '@/modules/task-center/core/types';
import { exchangeBalancesActivity, manualBalancesFetchActivity } from '@/modules/balances/balances.activity';
import { useBalanceStatus } from '@/modules/balances/use-balance-status';
import { bankBalancesActivity } from '@/modules/banks/banks.activity';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

interface UseLocationBalanceStatusReturn {
  /** Nothing has loaded for this location yet and its first load is running: show skeletons. */
  isInitialLoading: ComputedRef<boolean>;
  /** Its balances are being fetched again while the last ones stay on screen. */
  isRefreshing: ComputedRef<boolean>;
}

/**
 * Balance loading for one location, rather than the app-wide `useBalancesLoading`.
 *
 * A full refresh queries every chain and exchange in turn, so the global flag stays on long after
 * this location's own numbers have arrived. A chain answers from its per-chain activity, an
 * exchange from the activity keyed by its location, a bank from the one bank refresh, and
 * anything else holds only manual balances.
 *
 * Read once per location: the page keys its sections by the identifier, so another location gets
 * a fresh instance instead of re-deciding the kind in place.
 */
export function useLocationBalanceStatus(identifier: string): UseLocationBalanceStatusReturn {
  const { matchChain } = useSupportedChains();
  const chain = matchChain(identifier);
  if (chain) {
    const { isInitialLoading, isRefreshing } = useBalanceStatus(chain);
    return { isInitialLoading, isRefreshing };
  }

  const { allExchanges, banks } = storeToRefs(useLocationStore());
  const { useWorkStatus } = useTaskOrchestrator();

  const bankStatus = useWorkStatus(bankBalancesActivity.kind);
  const exchangeStatus = useWorkStatus(exchangeBalancesActivity.kind, ...exchangeBalancesActivity.partsOf({ location: identifier }));
  const manualStatus = useWorkStatus(manualBalancesFetchActivity.kind);

  const status = computed<WorkStatus>(() => {
    if (get(banks).includes(identifier))
      return get(bankStatus);
    if (get(allExchanges).includes(identifier))
      return get(exchangeStatus);
    return get(manualStatus);
  });

  return {
    isInitialLoading: computed<boolean>(() => get(status).active && !get(status).everCompleted),
    isRefreshing: computed<boolean>(() => get(status).active && get(status).everCompleted),
  };
}
