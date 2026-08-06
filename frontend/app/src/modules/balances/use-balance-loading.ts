import type { ComputedRef } from 'vue';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseBalancesLoadingReturn {
  loadingBalances: ComputedRef<boolean>;
  loadingBalancesAndDetection: ComputedRef<boolean>;
}

export function useBalancesLoading(): UseBalancesLoadingReturn {
  const { useIsActive } = useTaskCenter();

  // Every balance source now runs native, so liveness comes entirely off the orchestrator
  // (which also covers the queued/pending window the task store could not see).

  const loadingBalances = logicOr(
    useIsActive(ActivityKind.ALL_BALANCES),
    useIsActive(ActivityKind.BLOCKCHAIN_BALANCES),
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
  };
}
