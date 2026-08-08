import type { ComputedRef } from 'vue';
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
 * source of that liveness impossible to change: the cached read is due to stop being an activity,
 * and every direct reader would silently go dark for the whole cached phase — an empty dashboard
 * that looks settled rather than loading.
 */
export function useBalancesLoading(): UseBalancesLoadingReturn {
  const { useIsActive } = useTaskCenter();

  // Every balance source now runs native, so liveness comes entirely off the orchestrator
  // (which also covers the queued/pending window the task store could not see).

  const loadingBlockchainBalances = useIsActive(ActivityKind.BLOCKCHAIN_BALANCES);

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
