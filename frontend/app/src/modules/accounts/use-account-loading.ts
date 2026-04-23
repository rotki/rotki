import type { ComputedRef, Ref } from 'vue';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';

interface UseAccountLoadingReturn {
  pending: Ref<boolean>;
  loading: ComputedRef<boolean>;
  isAccountOperationRunning: (blockchain?: string) => ComputedRef<boolean>;
}

export const useAccountLoading = createSharedComposable((): UseAccountLoadingReturn => {
  const pending = ref<boolean>(false);

  const { useIsTaskRunning } = useTaskStore();
  const { isRefreshing } = storeToRefs(useBalanceRefreshState());

  const isAccountOperationRunning = (blockchain?: string): ComputedRef<boolean> =>
    logicOr(
      useIsTaskRunning(TaskType.ADD_ACCOUNT, blockchain ? { blockchain } : {}),
      useIsTaskRunning(TaskType.REMOVE_ACCOUNT, blockchain ? { blockchain } : {}),
    );

  const loading: ComputedRef<boolean> = logicOr(isAccountOperationRunning(), pending, isRefreshing);

  return {
    isAccountOperationRunning,
    loading,
    pending,
  };
});
