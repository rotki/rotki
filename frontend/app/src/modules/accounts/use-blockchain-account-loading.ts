import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import { useTokenDetectionStore } from '@/modules/balances/blockchain/use-token-detection-store';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { isTerminalStatus } from '@/modules/task-center/core/status';
import { ActivityKind, ActivityPart, activityParts } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

interface UseBlockchainAccountLoadingReturn {
  isDetectingTokens: ComputedRef<boolean>;
  refreshDisabled: ComputedRef<boolean>;
  deleteDisabled: ComputedRef<boolean>;
  isSectionLoading: ComputedRef<boolean>;
  operationRunning: ComputedRef<boolean>;
  isLoadingActive: ComputedRef<boolean>;
}

export function useBlockchainAccountLoading(category: MaybeRefOrGetter<string> = ''): UseBlockchainAccountLoadingReturn {
  const { useIsActivePrefix } = useTaskCenter();
  const { activities } = useTaskOrchestrator();
  const { massDetecting } = storeToRefs(useTokenDetectionStore());
  const { busyChains } = storeToRefs(useBalanceRefreshState());

  const { chainIds, isEvm } = useAccountCategoryHelper(category);

  // Reads the live activities rather than a per-chain `useWorkStatus`, because the chain set is
  // itself reactive. Matching on the id's first part covers the network refresh
  // (`blockchain-balances:<chain>`); hydration has no activity and is folded in below.
  const isAnyBalancesFetching = computed<boolean>(() => {
    const fetching = get(activities).filter(activity =>
      activity.kind === ActivityKind.BLOCKCHAIN_BALANCES && !isTerminalStatus(activity.status));

    if (!toValue(category))
      return fetching.length > 0;

    const chains = new Set(get(chainIds));
    return fetching.some(activity => chains.has(String(activityParts(activity.id)[0])));
  });

  // `isAnyBalancesFetching` already narrows to the category, so what is left to add is everything
  // the orchestrator does not own: an in-flight refresh POST and a hydration read, both tracked by
  // `useBalanceRefreshState` rather than by an activity status.
  const isSectionLoading = computed<boolean>(() => {
    if (get(isAnyBalancesFetching))
      return true;

    const busy = get(busyChains);
    return toValue(category)
      ? get(chainIds).some(chain => busy.has(chain))
      : busy.size > 0;
  });

  const isDetectingTokens = computed<boolean>(() => get(isEvm) && isDefined(massDetecting));
  const operationRunning = logicOr(useIsActivePrefix(ActivityKind.ACCOUNTS, ActivityPart.ADD), useIsActivePrefix(ActivityKind.ACCOUNTS, ActivityPart.REMOVE));
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
