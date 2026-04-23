import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import { useTokenDetectionStore } from '@/modules/balances/blockchain/use-token-detection-store';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { Section } from '@/modules/core/common/status';
import { useStatusStore } from '@/modules/core/common/use-status-store';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';

interface UseBlockchainAccountLoadingReturn {
  isDetectingTokens: ComputedRef<boolean>;
  refreshDisabled: ComputedRef<boolean>;
  deleteDisabled: ComputedRef<boolean>;
  isSectionLoading: ComputedRef<boolean>;
  operationRunning: ComputedRef<boolean>;
  isLoadingActive: ComputedRef<boolean>;
}

export function useBlockchainAccountLoading(category: MaybeRefOrGetter<string> = ''): UseBlockchainAccountLoadingReturn {
  const { isTaskRunning, useIsTaskRunning } = useTaskStore();
  const { massDetecting } = storeToRefs(useTokenDetectionStore());
  const { getIsLoading } = useStatusStore();
  const { refreshingChains } = storeToRefs(useBalanceRefreshState());

  const { chainIds, isEvm } = useAccountCategoryHelper(category);

  const isAnyBalancesFetching = computed<boolean>(() => {
    if (!toValue(category)) {
      return isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES)
        || isTaskRunning(TaskType.L2_LOOPRING);
    }

    if (get(chainIds).some(chain => isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES, { blockchain: chain })))
      return true;

    return get(isEvm) && isTaskRunning(TaskType.L2_LOOPRING);
  });

  const isSectionLoading = computed<boolean>(() => {
    const refreshing = get(refreshingChains);
    if (!toValue(category))
      return getIsLoading(Section.BLOCKCHAIN) || refreshing.size > 0;

    return get(chainIds).some(chain => getIsLoading(Section.BLOCKCHAIN, chain) || refreshing.has(chain));
  });

  const isDetectingTokens = computed<boolean>(() => get(isEvm) && isDefined(massDetecting));
  const operationRunning = logicOr(useIsTaskRunning(TaskType.ADD_ACCOUNT), useIsTaskRunning(TaskType.REMOVE_ACCOUNT));
  const refreshDisabled = logicOr(isSectionLoading, isDetectingTokens);
  const deleteDisabled = logicOr(isAnyBalancesFetching, operationRunning);
  const isLoadingActive = logicOr(isDetectingTokens, isSectionLoading, operationRunning);

  return {
    deleteDisabled,
    isDetectingTokens,
    isSectionLoading,
    operationRunning,
    refreshDisabled,
    isLoadingActive,
  };
}
