import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { Section, Status } from '@/modules/core/common/status';
import { useStatusStore } from '@/modules/core/common/use-status-store';

interface UseBalanceStatusReturn {
  hasCachedData: ComputedRef<boolean>;
  isInitialLoading: ComputedRef<boolean>;
  isRefreshing: ComputedRef<boolean>;
}

export function isCacheInitialLoading(status: Status | undefined): boolean {
  return status === undefined || status === Status.NONE || status === Status.LOADING;
}

/**
 * Per-chain or aggregate view of blockchain balance loading.
 *
 * Aggregate semantics (no chain arg):
 * - hasCachedData: at least one touched chain has reached LOADED
 * - isInitialLoading: at least one touched chain is still LOADING/NONE
 * - isRefreshing: at least one chain has an in-flight refresh POST
 */
export function useBalanceStatus(chain?: MaybeRefOrGetter<string>): UseBalanceStatusReturn {
  const statusStore = useStatusStore();
  const { status } = storeToRefs(statusStore);
  const { getStatus } = statusStore;
  const refreshState = useBalanceRefreshState();

  const hasCachedData = computed<boolean>(() => {
    const target = toValue(chain);
    if (target !== undefined)
      return getStatus(Section.BLOCKCHAIN, target) === Status.LOADED;

    const chains = get(status)[Section.BLOCKCHAIN];
    if (!chains)
      return false;
    return Object.values(chains).includes(Status.LOADED);
  });

  const isInitialLoading = computed<boolean>(() => {
    const target = toValue(chain);
    if (target !== undefined)
      return isCacheInitialLoading(getStatus(Section.BLOCKCHAIN, target));

    const chains = get(status)[Section.BLOCKCHAIN];
    if (!chains)
      return false;
    return Object.values(chains).some(isCacheInitialLoading);
  });

  const { isRefreshing: anyIsRefreshing } = storeToRefs(refreshState);
  const isRefreshing = chain === undefined
    ? anyIsRefreshing
    : refreshState.useIsRefreshing(chain);

  return {
    hasCachedData,
    isInitialLoading,
    isRefreshing,
  };
}
