import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import { useAccountCategoryHelper } from '@/composables/accounts/use-account-category-helper';
import { useBlockchainTokensStore } from '@/store/blockchain/tokens';
import { useStatusStore } from '@/store/status';
import { useTaskStore } from '@/store/tasks';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';

interface UseBlockchainAccountLoadingReturn {
  isDetectingTokens: ComputedRef<boolean>;
  refreshDisabled: ComputedRef<boolean>;
  deleteDisabled: ComputedRef<boolean>;
  isSectionLoading: ComputedRef<boolean>;
  operationRunning: ComputedRef<boolean>;
}

export function useBlockchainAccountLoading(category: MaybeRef<string> = ''): UseBlockchainAccountLoadingReturn {
  const { isTaskRunning } = useTaskStore();
  const { massDetecting } = storeToRefs(useBlockchainTokensStore());
  const { isLoading } = useStatusStore();

  const { chainIds, isEvm } = useAccountCategoryHelper(category);

  const isAnyBalancesFetching = computed(() => {
    if (!category) {
      return get(logicOr(
        isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES),
        isTaskRunning(TaskType.L2_LOOPRING),
      ));
    }

    const chainsTask = get(chainIds).map(chain => isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES, { blockchain: chain }));

    if (get(isEvm)) {
      chainsTask.push(isTaskRunning(TaskType.L2_LOOPRING));
    }

    return get(logicOr(...(chainsTask)));
  });

  const isSectionLoading = computed(() => {
    if (!category)
      return get(isLoading(Section.BLOCKCHAIN));

    const chainsTask = get(chainIds).map(chain => isLoading(Section.BLOCKCHAIN, chain));
    return get(logicOr(...(chainsTask)));
  });

  const isDetectingTokens = computed(() => get(isEvm) && isDefined(massDetecting));
  const operationRunning = logicOr(isTaskRunning(TaskType.ADD_ACCOUNT), isTaskRunning(TaskType.REMOVE_ACCOUNT));
  const refreshDisabled = logicOr(isSectionLoading, isDetectingTokens);
  const deleteDisabled = logicOr(isAnyBalancesFetching, operationRunning);

  return {
    deleteDisabled,
    isDetectingTokens,
    isSectionLoading,
    operationRunning,
    refreshDisabled,
  };
}
