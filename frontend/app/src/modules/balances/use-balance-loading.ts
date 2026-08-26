import type { ComputedRef } from 'vue';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseBalancesLoadingReturn {
  /** Blockchain balances only — the narrow read most spinners actually want. */
  loadingBlockchainBalances: ComputedRef<boolean>;
  loadingBalances: ComputedRef<boolean>;
  loadingBalancesAndDetection: ComputedRef<boolean>;
}

/**
 * The single definition of "balances are loading".
 *
 * @remarks
 * Read liveness from here, not from `useIsActive(BLOCKCHAIN_BALANCES)`. Hydration is not an
 * activity, so the orchestrator alone reads as settled for the whole cached phase.
 */
export function useBalancesLoading(): UseBalancesLoadingReturn {
  const { useIsActive } = useTaskCenter();
  const { isHydrating } = storeToRefs(useBalanceRefreshState());

  const loadingBlockchainBalances = logicOr(
    useIsActive(ActivityKind.BLOCKCHAIN_BALANCES),
    isHydrating,
  );

  const loadingBalances = logicOr(
    useIsActive(ActivityKind.ALL_BALANCES),
    loadingBlockchainBalances,
    useIsActive(ActivityKind.EXCHANGE_BALANCES),
    useIsActive(ActivityKind.MANUAL_BALANCES),
  );

  const loadingBalancesAndDetection = logicOr(
    loadingBalances,
    useIsActive(ActivityKind.TOKEN_DETECTION),
  );

  return {
    loadingBalances,
    loadingBalancesAndDetection,
    loadingBlockchainBalances,
  };
}
