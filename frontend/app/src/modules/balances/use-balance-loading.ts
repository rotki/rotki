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
 * ⚠️ Read liveness from here rather than calling `useIsActive(ActivityKind.BLOCKCHAIN_BALANCES)`
 * directly. Consumers spread across the app reading the orchestrator themselves is what makes the
 * source of that liveness impossible to change — and it has now changed: hydration is no longer an
 * activity, so a direct reader goes silently dark for the whole cached phase, showing an empty
 * dashboard that looks settled rather than loading.
 */
export function useBalancesLoading(): UseBalancesLoadingReturn {
  const { useIsActive } = useTaskCenter();
  const { isHydrating } = storeToRefs(useBalanceRefreshState());

  // Two sources, because there are two layers. Work is the orchestrator's (which also covers the
  // queued/pending window the task store could not see); hydration is not an activity at all, so
  // its liveness comes off the refresh-state store.
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
