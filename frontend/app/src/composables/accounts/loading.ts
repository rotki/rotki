import { TaskType } from '@/types/task-type';

export const useAccountLoading = createSharedComposable(() => {
  const pending = ref<boolean>(false);

  const { isTaskRunning } = useTaskStore();

  const isQueryingBlockchain = isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);
  const isLoopringLoading = isTaskRunning(TaskType.L2_LOOPRING);

  const isBlockchainLoading = computed<boolean>(() => get(isQueryingBlockchain) || get(isLoopringLoading));

  const isAccountOperationRunning = (blockchain?: string): ComputedRef<boolean> =>
    logicOr(
      isTaskRunning(TaskType.ADD_ACCOUNT, blockchain ? { blockchain } : {}),
      isTaskRunning(TaskType.REMOVE_ACCOUNT, blockchain ? { blockchain } : {}),
    );

  const loading: ComputedRef<boolean> = logicOr(isAccountOperationRunning(), pending, isQueryingBlockchain);

  return {
    pending,
    loading,
    isQueryingBlockchain,
    isBlockchainLoading,
    isAccountOperationRunning,
  };
});
