import { type ComputedRef } from 'vue';
import { type Blockchain } from '@rotki/common/lib/blockchain';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

export const useAccountLoading = () => {
  const pending = ref<boolean>(false);

  const { isTaskRunning } = useTasks();

  const isQueryingBlockchain = isTaskRunning(
    TaskType.QUERY_BLOCKCHAIN_BALANCES
  );
  const isLoopringLoading = isTaskRunning(TaskType.L2_LOOPRING);

  const isBlockchainLoading: ComputedRef<boolean> = computed(() => {
    return get(isQueryingBlockchain) || get(isLoopringLoading);
  });

  const isAccountOperationRunning = (
    blockchain?: Blockchain
  ): ComputedRef<boolean> =>
    logicOr(
      isTaskRunning(TaskType.ADD_ACCOUNT, blockchain ? { blockchain } : {}),
      isTaskRunning(TaskType.REMOVE_ACCOUNT, blockchain ? { blockchain } : {})
    );

  const loading: ComputedRef<boolean> = logicOr(
    isAccountOperationRunning(),
    pending,
    isQueryingBlockchain
  );

  return {
    pending,
    loading,
    isQueryingBlockchain,
    isBlockchainLoading,
    isAccountOperationRunning
  };
};
