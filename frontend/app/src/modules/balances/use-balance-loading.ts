import type { ComputedRef } from 'vue';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';

interface UseBalancesLoadingReturn {
  loadingBalances: ComputedRef<boolean>;
  loadingBalancesAndDetection: ComputedRef<boolean>;
}

export function useBalancesLoading(): UseBalancesLoadingReturn {
  const { useIsTaskRunning } = useTaskStore();

  const loadingBalances = logicOr(
    useIsTaskRunning(TaskType.QUERY_BALANCES),
    useIsTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES),
    useIsTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES),
    useIsTaskRunning(TaskType.MANUAL_BALANCES),
    useIsTaskRunning(TaskType.L2_LOOPRING),
  );

  const loadingBalancesAndDetection = logicOr(
    loadingBalances,
    useIsTaskRunning(TaskType.FETCH_DETECTED_TOKENS),
  );

  return {
    loadingBalances,
    loadingBalancesAndDetection,
  };
}
