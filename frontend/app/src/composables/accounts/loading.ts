import type { ComputedRef, Ref } from 'vue';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

interface UseAccountLoadingReturn {
  pending: Ref<boolean>;
  loading: ComputedRef<boolean>;
  isQueryingBlockchain: ComputedRef<boolean>;
  isBlockchainLoading: ComputedRef<boolean>;
  isAccountOperationRunning: (blockchain?: string) => ComputedRef<boolean>;
}

export const useAccountLoading = createSharedComposable((): UseAccountLoadingReturn => {
  const pending = ref<boolean>(false);

  const { useIsTaskRunning } = useTaskStore();

  const isQueryingBlockchain = useIsTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);
  const isLoopringLoading = useIsTaskRunning(TaskType.L2_LOOPRING);

  const isBlockchainLoading = computed<boolean>(() => get(isQueryingBlockchain) || get(isLoopringLoading));

  const isAccountOperationRunning = (blockchain?: string): ComputedRef<boolean> =>
    logicOr(
      useIsTaskRunning(TaskType.ADD_ACCOUNT, blockchain ? { blockchain } : {}),
      useIsTaskRunning(TaskType.REMOVE_ACCOUNT, blockchain ? { blockchain } : {}),
    );

  const loading: ComputedRef<boolean> = logicOr(isAccountOperationRunning(), pending, isQueryingBlockchain);

  return {
    isAccountOperationRunning,
    isBlockchainLoading,
    isQueryingBlockchain,
    loading,
    pending,
  };
});
