import { TaskType } from '@/types/task-type';
import { Section } from '@/types/status';

interface UseBlockchainAccountLoadingReturn {
  isDetectingTokens: ComputedRef<boolean>;
  refreshDisabled: ComputedRef<boolean>;
  deleteDisabled: ComputedRef<boolean>;
}

export function useBlockchainAccountLoading(refresh: () => Promise<void>): UseBlockchainAccountLoadingReturn {
  const { isTaskRunning } = useTaskStore();
  const { massDetecting } = storeToRefs(useBlockchainTokensStore());
  const { isLoading } = useStatusStore();

  const isAnyBalancesFetching = logicOr(
    isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES),
    isTaskRunning(TaskType.L2_LOOPRING),
  );

  const isSectionLoading = isLoading(Section.BLOCKCHAIN);
  const isDetectingTokens = computed(() => isDefined(massDetecting));
  const operationRunning = logicOr(isTaskRunning(TaskType.ADD_ACCOUNT), isTaskRunning(TaskType.REMOVE_ACCOUNT));
  const refreshDisabled = logicOr(isSectionLoading, isDetectingTokens);
  const deleteDisabled = logicOr(isAnyBalancesFetching, operationRunning);

  watchDebounced(
    logicOr(isDetectingTokens, isSectionLoading, operationRunning),
    async (isLoading, wasLoading) => {
      if (!isLoading && wasLoading)
        await refresh();
    },
    {
      debounce: 800,
    },
  );

  return {
    isDetectingTokens,
    refreshDisabled,
    deleteDisabled,
  };
}
